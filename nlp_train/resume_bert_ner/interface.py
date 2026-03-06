import torch
import torch.nn as nn
from transformers import BertPreTrainedModel, BertModel, AutoTokenizer
import pdfplumber
import os
import json
import numpy as np

# ==========================================
# 1. 必须与训练代码完全一致的配置
# ==========================================
class Config:
    model_name = "hfl/chinese-roberta-wwm-ext"
    num_classes = 18
    max_len = 512
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    categories = [
        "姓名", "出生年月", "性别", "电话", "最高学历", "籍贯", "落户市县", 
        "政治面貌", "毕业院校", "工作单位", "工作内容", "职务", 
        "项目名称", "项目责任", "学位", "毕业时间", "工作时间", "项目时间"
    ]
    model_path = "./model_output_backup/best_model.pth"

# 复制 GlobalPointer 和 ResumeNERModel 类
# (为了保证运行，请务必把 train_pro.py 里的 GlobalPointer 和 ResumeNERModel 类复制到这里！)
# !!! 必须复制 !!! 
# (此处省略类定义，假设你已经复制了，或者它们在同一个包里)
# 为方便你直接运行，我这里再贴一次简化版，确保你粘贴就能跑

class GlobalPointer(nn.Module):
    def __init__(self, input_dim, heads, head_size=64, rope=True):
        super().__init__()
        self.heads = heads
        self.head_size = head_size
        self.rope = rope
        self.dense = nn.Linear(input_dim, heads * head_size * 2)

    def forward(self, inputs, mask=None):
        inputs = self.dense(inputs) 
        bw, seq_len, _ = inputs.shape
        inputs = inputs.view(bw, seq_len, self.heads, self.head_size * 2)
        qw, kw = inputs[..., :self.head_size], inputs[..., self.head_size:]
        if self.rope:
            pos = torch.arange(seq_len, device=inputs.device).unsqueeze(-1)
            indices = torch.arange(0, self.head_size, 2, dtype=torch.float32, device=inputs.device)
            sin_inp = torch.sin(pos / 10000**(indices / self.head_size))
            cos_inp = torch.cos(pos / 10000**(indices / self.head_size))
            sin_inp = torch.repeat_interleave(sin_inp, 2, dim=-1)
            cos_inp = torch.repeat_interleave(cos_inp, 2, dim=-1)
            sin_inp = sin_inp.unsqueeze(0).unsqueeze(2)
            cos_inp = cos_inp.unsqueeze(0).unsqueeze(2)
            qw2 = torch.stack([-qw[..., 1::2], qw[..., ::2]], dim=-1).reshape_as(qw)
            qw = qw * cos_inp + qw2 * sin_inp
            kw2 = torch.stack([-kw[..., 1::2], kw[..., ::2]], dim=-1).reshape_as(kw)
            kw = kw * cos_inp + kw2 * sin_inp
        logits = torch.einsum('bmhd,bnhd->bhmn', qw, kw)
        if mask is not None:
            mask = mask.unsqueeze(1).unsqueeze(1)
            logits = logits - (1 - mask) * 1e12
            logits = logits - (1 - mask.transpose(-1, -2)) * 1e12
        mask_tri = torch.tril(torch.ones_like(logits), diagonal=-1) 
        logits = logits - mask_tri * 1e12
        return logits / self.head_size**0.5

class ResumeNERModel(BertPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.bert = BertModel(config)
        self.global_pointer = GlobalPointer(config.hidden_size, Config.num_classes, head_size=64, rope=True)

    def forward(self, input_ids, attention_mask=None):
        outputs = self.bert(input_ids, attention_mask=attention_mask)
        return self.global_pointer(outputs.last_hidden_state, mask=attention_mask)

# ==========================================
# 2. 增强版推理
# ==========================================
class InferenceEngine:
    def __init__(self):
        print(">>> 初始化推理引擎...")
        self.tokenizer = AutoTokenizer.from_pretrained(Config.model_name)
        self.model = ResumeNERModel.from_pretrained(Config.model_name)
        
        if os.path.exists(Config.model_path):
            print(f">>> 加载模型权重: {Config.model_path}")
            # strict=False 防止一些无关紧要的层报错，但这里应该完全匹配
            state = torch.load(Config.model_path, map_location=Config.device)
            self.model.load_state_dict(state)
        else:
            print("!!! 警告：模型文件不存在，预测结果将是随机的！")
            
        self.model.to(Config.device)
        self.model.eval()

    def predict(self, pdf_path):
        # 1. 解析
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t: text += t + "\n"
        except Exception as e:
            return {"error": str(e)}

        if not text: return {"error": "PDF解析内容为空"}
        
        print(f">>> PDF解析成功，长度: {len(text)} 字符")
        print(f">>> 文本前50字预览: {text[:50]}...")

        # 2. Tokenize
        # 注意：return_offsets_mapping 是关键，用于将 Token 下标映射回原文字符
        inputs = self.tokenizer(
            text, 
            max_length=Config.max_len, 
            truncation=True, 
            return_offsets_mapping=True, 
            return_tensors="pt"
        )
        
        input_ids = inputs['input_ids'].to(Config.device)
        mask = inputs['attention_mask'].to(Config.device)
        offset_mapping = inputs['offset_mapping'][0].cpu().numpy()
        
        # 3. 预测
        with torch.no_grad():
            # logits: [1, num_classes, seq_len, seq_len]
            logits = self.model(input_ids, attention_mask=mask)
        
        logits = logits[0].cpu().numpy()
        
        # 4. 调试信息 (关键一步)
        max_score = np.max(logits)
        print(f">>> 预测Logits最大值: {max_score:.4f}")
        if max_score < 0:
            print("!!! 警告：最大Logits小于0，说明模型认为没有实体。可能是模型欠拟合，或阈值需要调整。")
            threshold = -1.0 # 强制调低阈值看看有没有东西
        else:
            threshold = 0.0

        # 5. 解码
        results = {}
        for idx, cat in enumerate(Config.categories):
            matrix = logits[idx] # [seq, seq]
            
            # 筛选大于阈值的位置
            start_idxs, end_idxs = np.where(matrix > threshold)
            
            items = []
            for s, e in zip(start_idxs, end_idxs):
                if s > e: continue
                
                # 映射回字符
                char_s = offset_mapping[s][0]
                char_e = offset_mapping[e][1]
                
                if char_s == 0 and char_e == 0: continue
                
                val = text[char_s:char_e]
                if val and val not in items:
                    items.append(val)
            
            if items:
                results[cat] = items
                
        return results

if __name__ == "__main__":
    engine = InferenceEngine()
    # 替换为你实际的测试文件
    res = engine.predict("./data/test_resume.pdf")
    
    print("\n" + "="*30)
    print("最终提取结果:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print("="*30)