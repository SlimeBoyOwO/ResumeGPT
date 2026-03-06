import os
# 1. 必须在导入 torch 之前设置环境变量
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader, Dataset
from transformers import BertPreTrainedModel, BertModel, AutoTokenizer, get_linear_schedule_with_warmup
from torch.optim import AdamW
from tqdm import tqdm
import json
import pdfplumber
import pickle
import gc # 引入垃圾回收
from sklearn.model_selection import train_test_split
from torch.amp.autocast_mode import autocast
from torch.amp.grad_scaler import GradScaler

# ==========================================
# 1. 配置参数
# ==========================================
class Config:
    model_name = "hfl/chinese-roberta-wwm-ext"
    num_classes = 18
    max_len = 512
    # 5070Ti 推荐 16。如果显存溢出，请改为 8
    batch_size = 16 
    epochs = 15
    lr = 2e-5 
    patience = 3
    max_grad_norm = 1.0
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    adv_train = True # 开启对抗训练
    
    json_path = "./data/train_data.json"
    pdf_folder = "./data/pdf_files/"
    cache_path = "./data/processed_tensors_cache.pkl" 
    save_path = "./model_output/" 

if not os.path.exists(Config.save_path):
    os.makedirs(Config.save_path)

# ==========================================
# 2. Loss & Model (FP32 防护)
# ==========================================
class GlobalPointerLoss(nn.Module):
    def __init__(self):
        super().__init__()

    def forward(self, y_pred, y_true):
        # 强制转为 FP32，防止 NaN
        y_pred = y_pred.float()
        y_true = y_true.float()
        
        shape = y_pred.shape
        y_true = y_true.reshape(shape[0] * shape[1], -1)
        y_pred = y_pred.reshape(shape[0] * shape[1], -1)

        y_neg = y_pred - y_true * 1e12
        y_pos = -y_pred - (1 - y_true) * 1e12
        
        zeros = torch.zeros_like(y_pred[..., :1])
        y_neg = torch.cat([y_neg, zeros], dim=-1)
        y_pos = torch.cat([y_pos, zeros], dim=-1)
        
        neg_loss = torch.logsumexp(y_neg, dim=-1)
        pos_loss = torch.logsumexp(y_pos, dim=-1)
        return (neg_loss + pos_loss).mean()

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
            mask_expanded = mask.unsqueeze(1).unsqueeze(1)
            logits = logits - (1 - mask_expanded) * 1e12
            logits = logits - (1 - mask_expanded.transpose(-1, -2)) * 1e12

        mask_tri = torch.tril(torch.ones_like(logits), diagonal=-1) 
        logits = logits - mask_tri * 1e12
        return logits / self.head_size**0.5

class ResumeNERModel(BertPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.bert = BertModel(config)
        self.global_pointer = GlobalPointer(config.hidden_size, Config.num_classes, head_size=64, rope=True)
        self.loss_fn = GlobalPointerLoss()

    def forward(self, input_ids, attention_mask=None, token_type_ids=None, labels=None):
        outputs = self.bert(input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        sequence_output = outputs.last_hidden_state
        logits = self.global_pointer(sequence_output, mask=attention_mask)
        loss = None
        if labels is not None:
            loss = self.loss_fn(logits, labels)
        return loss, logits

class FGM:
    def __init__(self, model):
        self.model = model
        self.backup = {}
    def attack(self, epsilon=1., emb_name='word_embeddings'):
        for name, param in self.model.named_parameters():
            if param.requires_grad and emb_name in name:
                self.backup[name] = param.data.clone()
                norm = torch.norm(param.grad)
                if norm != 0 and not torch.isnan(norm):
                    r_at = epsilon * param.grad / norm
                    param.data.add_(r_at)
    def restore(self, emb_name='word_embeddings'):
        for name, param in self.model.named_parameters():
            if param.requires_grad and emb_name in name:
                assert name in self.backup
                param.data = self.backup[name]
        self.backup = {}

# ==========================================
# 3. 极速数据处理
# ==========================================
def extract_text_from_pdf(pdf_path):
    text_content = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt: text_content += txt + "\n"
    except:
        return ""
    return text_content

def process_and_cache_data(json_path, pdf_folder):
    import os
    if os.path.exists(Config.cache_path):
        print(f"--> 🚀 发现极速缓存: {Config.cache_path}，加载中...")
        with open(Config.cache_path, 'rb') as f:
            return pickle.load(f)

    print(f"--> 未发现缓存，开始全量预处理...")
    tokenizer = AutoTokenizer.from_pretrained(Config.model_name)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # 必须保持顺序一致
    categories = [
        "姓名", "出生年月", "性别", "电话", "最高学历", "籍贯", "落户市县", 
        "政治面貌", "毕业院校", "工作单位", "工作内容", "职务", 
        "项目名称", "项目责任", "学位", "毕业时间", "工作时间", "项目时间"
    ]
    target_categories = set(categories)
    cat2id = {c: i for i, c in enumerate(categories)}

    processed_samples = []
    
    for resume_id, content in tqdm(raw_data.items(), desc="Preprocessing"):
        import os
        pdf_path = os.path.join(pdf_folder, f"{resume_id}.pdf")
        if not os.path.exists(pdf_path): continue
        text = extract_text_from_pdf(pdf_path)
        if not text: continue
        
        labels_raw = []
        def find_label(k, v):
            if k not in target_categories or not v: return
            start = text.find(v)
            while start != -1:
                labels_raw.append([start, start+len(v), k])
                start = text.find(v, start+1)

        for k, v in content.items():
            if isinstance(v, str): find_label(k, v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        for sk, sv in item.items(): find_label(sk, sv)
        
        if not labels_raw: continue

        encoding = tokenizer(
            text, 
            max_length=Config.max_len, 
            padding='max_length', 
            truncation=True, 
            return_offsets_mapping=True, 
            return_tensors="pt"
        )
        
        input_ids = encoding['input_ids'].squeeze()
        attention_mask = encoding['attention_mask'].squeeze()
        offset_mapping = encoding['offset_mapping'].squeeze()
        
        # 使用 float32 保证精度，如果内存不够可以改 float16
        label_matrix = torch.zeros((Config.num_classes, Config.max_len, Config.max_len), dtype=torch.float32)
        
        for start_c, end_c, type_ in labels_raw:
            if type_ not in cat2id: continue
            cid = cat2id[type_]
            s_tok, e_tok = None, None
            
            for i, (os, oe) in enumerate(offset_mapping):
                if os == 0 and oe == 0: continue
                if os == start_c: s_tok = i
                if oe == end_c: e_tok = i
            
            if s_tok is None or e_tok is None:
                for i, (os, oe) in enumerate(offset_mapping):
                    if os <= start_c < oe: s_tok = i
                    if os < end_c <= oe: e_tok = i
            
            if s_tok is not None and e_tok is not None and s_tok < Config.max_len and e_tok < Config.max_len:
                label_matrix[cid, s_tok, e_tok] = 1.0
        
        processed_samples.append({
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'labels': label_matrix
        })

    print(f"--> 预处理完成，保存中...")
    with open(Config.cache_path, 'wb') as f:
        pickle.dump(processed_samples, f)
    
    # 手动释放内存
    del raw_data
    gc.collect()
    
    return processed_samples

class FastResumeDataset(Dataset):
    def __init__(self, data):
        self.data = data
    def __len__(self): return len(self.data)
    def __getitem__(self, idx): return self.data[idx]

# ==========================================
# 4. 实体级评估 (Entity F1)
# ==========================================
def evaluate_entity_level(model, dataloader, device):
    model.eval()
    X, Y, Z = 1e-10, 1e-10, 1e-10
    
    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Evaluating (Entity Level)"):
            input_ids = batch['input_ids'].to(device)
            mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            
            _, logits = model(input_ids, attention_mask=mask)
            pred = (logits > 0).float()
            
            # 只统计上三角 (合法实体)
            mask_tri = torch.triu(torch.ones_like(pred), diagonal=0)
            pred = pred * mask_tri
            labels = labels * mask_tri
            
            X += (pred * labels).sum().item()
            Y += pred.sum().item()
            Z += labels.sum().item()
            
    f1 = 2 * X / (Y + Z)
    p = X / Y
    r = X / Z
    return f1, p, r

# ==========================================
# 5. 训练主循环 (修复 Unscale 重复调用)
# ==========================================
def train():
    all_data = process_and_cache_data(Config.json_path, Config.pdf_folder)
    train_data, val_data = train_test_split(all_data, test_size=0.1, random_state=42)
    print(f"Train: {len(train_data)} | Val: {len(val_data)}")
    
    train_ds = FastResumeDataset(train_data)
    val_ds = FastResumeDataset(val_data)
    
    train_loader = DataLoader(train_ds, batch_size=Config.batch_size, shuffle=True, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=Config.batch_size, shuffle=False, pin_memory=True)
    
    model = ResumeNERModel.from_pretrained(Config.model_name)
    model.to(Config.device)
    
    optimizer = AdamW(model.parameters(), lr=Config.lr)
    
    total_steps = len(train_loader) * Config.epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=int(0.1*total_steps), num_training_steps=total_steps)
    scaler = GradScaler(device='cuda')
    fgm = FGM(model) if Config.adv_train else None
    
    best_f1 = 0.0
    early_stop_counter = 0
    
    print(f"🚀 开始极速训练 | Device: {Config.device} | Batch: {Config.batch_size}")
    
    for epoch in range(Config.epochs):
        model.train()
        total_loss = 0
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{Config.epochs}")
        
        for batch in pbar:
            input_ids = batch['input_ids'].to(Config.device)
            mask = batch['attention_mask'].to(Config.device)
            labels = batch['labels'].to(Config.device)
            
            optimizer.zero_grad()
            
            with autocast(device_type='cuda'):
                loss, _ = model(input_ids, attention_mask=mask, labels=labels)
            
            if torch.isnan(loss):
                print("⚠️ NaN Loss detected!")
                continue

            scaler.scale(loss).backward()
            
            # --- 核心修复区 ---
            if fgm:
                # 1. 既然要对抗，必须先 Unscale 拿到真实梯度
                scaler.unscale_(optimizer)
                
                # 2. 攻击
                fgm.attack()
                
                # 3. 对抗样本前向
                with autocast(device_type='cuda'):
                    loss_adv, _ = model(input_ids, attention_mask=mask, labels=labels)
                
                # 4. 对抗样本反向 (累加梯度)
                # 注意：这里不能再 scale 了，因为 optimizer 已经 unscaled 了
                # 标准做法是：loss_adv.backward()
                loss_adv.backward() 
                
                # 5. 恢复
                fgm.restore()
            else:
                # 如果没有 FGM，我们在 clip 之前必须 unscale
                # 如果有 FGM，上面已经 unscale 过了，这里就不能再调了
                scaler.unscale_(optimizer)
            # -----------------
            
            # 梯度裁剪 (此时 optimizer 已经被 unscale 过了，可以直接 clip)
            torch.nn.utils.clip_grad_norm_(model.parameters(), Config.max_grad_norm)
            
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            
            total_loss += loss.item()
            pbar.set_postfix({'loss': f"{loss.item():.4f}"})
        
        # 验证
        f1, p, r = evaluate_entity_level(model, val_loader, Config.device)
        print(f"Epoch {epoch+1} >> Entity F1: {f1:.4f} | P: {p:.4f} | R: {r:.4f}")
        
        if f1 > best_f1:
            best_f1 = f1
            early_stop_counter = 0
            save_file = os.path.join(Config.save_path, 'best_model.pth')
            torch.save(model.state_dict(), save_file)
            print(f"🔥 New Best F1! Model saved.")
        else:
            early_stop_counter += 1
            if early_stop_counter >= Config.patience:
                print("⛔ Early stopping.")
                break

if __name__ == "__main__":
    train()