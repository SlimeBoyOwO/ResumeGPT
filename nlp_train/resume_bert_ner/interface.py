import torch
import torch.nn as nn
from transformers import BertPreTrainedModel, BertModel, AutoTokenizer
import pdfplumber
import os
import json
import numpy as np

# ==========================================
# 1. 配置与模型定义 (保持你的原样)
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
    model_path = "./model_output/best_model.pth"

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
# 2. 增强版推理与后处理引擎
# ==========================================
class InferenceEngine:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(Config.model_name)
        self.model = ResumeNERModel.from_pretrained(Config.model_name)
        if os.path.exists(Config.model_path):
            state = torch.load(Config.model_path, map_location=Config.device)
            self.model.load_state_dict(state)
        self.model.to(Config.device)
        self.model.eval()

        # 定义用于重组的 Schema 结构
        self.schemas = {
            "教育经历": ["毕业时间", "毕业院校", "学位"],
            "工作经历": ["工作时间", "工作单位", "职务", "工作内容"],
            "项目经历": ["项目名称", "项目时间", "项目责任"]
        }
        # 基础字段（不需要嵌套的）
        self.basic_fields = ["姓名", "出生年月", "性别", "电话", "最高学历", "籍贯", "落户市县", "政治面貌"]

    def extract_text_from_pdf(self, pdf_path):
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t: text += t + "\n"
        except Exception as e:
            return ""
        return text

    def predict_chunk(self, text_chunk, global_offset=0):
        """处理单块文本，返回带有绝对位置的实体列表"""
        inputs = self.tokenizer(
            text_chunk, max_length=Config.max_len, truncation=True, 
            return_offsets_mapping=True, return_tensors="pt"
        )
        input_ids = inputs['input_ids'].to(Config.device)
        mask = inputs['attention_mask'].to(Config.device)
        offset_mapping = inputs['offset_mapping'][0].cpu().numpy()
        
        with torch.no_grad():
            logits = self.model(input_ids, attention_mask=mask)[0].cpu().numpy()
        
        threshold = 0.0
        entities = []
        for idx, cat in enumerate(Config.categories):
            matrix = logits[idx]
            start_idxs, end_idxs = np.where(matrix > threshold)
            for s, e in zip(start_idxs, end_idxs):
                if s > e: continue
                char_s = offset_mapping[s][0]
                char_e = offset_mapping[e][1]
                if char_s == 0 and char_e == 0: continue
                
                val = text_chunk[char_s:char_e]
                if val:
                    entities.append({
                        "category": cat,
                        "value": val,
                        "start": char_s + global_offset, # 记录在整篇文档中的绝对位置
                        "end": char_e + global_offset
                    })
        return entities

    def rebuild_nested_json(self, entities):
        """将带有位置信息的平铺实体，重组成嵌套 JSON"""
        # 按在文档中出现的先后顺序排序
        entities = sorted(entities, key=lambda x: x['start'])
        
        result = {
            "项目经历": [],
            "教育经历": [],
            "工作经历": []
        }
        
        # 1. 填充基础平铺字段
        for field in self.basic_fields:
            vals = [e['value'] for e in entities if e['category'] == field]
            if vals:
                result[field] = vals[0] # 取第一个出现的作为主属性
                
        # 2. 动态构建嵌套列表 (使用启发式聚类：根据出现的顺序分组)
        def build_list(block_key, block_fields):
            current_group = {}
            for e in entities:
                cat = e['category']
                if cat in block_fields:
                    # 如果当前组已经有了这个字段，说明开启了一段新经历
                    if cat in current_group:
                        result[block_key].append(current_group)
                        current_group = {}
                    current_group[cat] = e['value']
            # 把最后留在缓存里的一组加上去
            if current_group:
                result[block_key].append(current_group)

        # 构建三个大模块
        build_list("教育经历", self.schemas["教育经历"])
        build_list("工作经历", self.schemas["工作经历"])
        build_list("项目经历", self.schemas["项目经历"])

        # 清理空列表
        result = {k: v for k, v in result.items() if v}
        return result

    def predict(self, pdf_path):
        text = self.extract_text_from_pdf(pdf_path)
        if not text: return {"error": "PDF解析失败或为空"}
        
        # --- 滑动窗口推理，解决 512 截断问题 ---
        all_entities = []
        chunk_size = 450 # 预留 token 空间
        overlap = 50
        
        # 简单按字符滑动（不够严谨但能解决长文本遗漏问题）
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            chunk_entities = self.predict_chunk(chunk, global_offset=start)
            all_entities.extend(chunk_entities)
            if end == len(text):
                break
            start += (chunk_size - overlap)
            
        # 实体去重 (重叠部分可能会抽出一样的)
        unique_entities = []
        seen = set()
        for e in all_entities:
            identifier = f"{e['category']}-{e['start']}-{e['end']}"
            if identifier not in seen:
                seen.add(identifier)
                unique_entities.append(e)

        # --- 重组为嵌套 JSON ---
        final_json = self.rebuild_nested_json(unique_entities)
        return final_json

if __name__ == "__main__":
    engine = InferenceEngine()
    # 替换为你实际的测试文件
    res = engine.predict("./data/test_2.pdf")
    
    print("\n" + "="*50)
    print("✨ 修复后的结构化抽取结果:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    print("="*50)