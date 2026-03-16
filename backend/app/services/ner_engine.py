# -*- coding: utf-8 -*-
"""BERT-based NER inference for resumes."""

from __future__ import annotations

import os
# 彻底禁用联网和自动转换
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pdfplumber
import torch
import torch.nn as nn
from transformers import AutoTokenizer, BertModel, BertPreTrainedModel


@dataclass(frozen=True)
class NerConfig:
    model_name: str = "hfl/chinese-roberta-wwm-ext"
    num_classes: int = 18
    max_len: int = 512
    chunk_size: int = 450
    overlap: int = 50
    model_path: Path = Path(__file__).resolve().parent.parent / "ner_model" / "best_model.pth"


NerCategories = [
    "姓名", "出生年月", "性别", "电话", "最高学历", "籍贯", "现居市县", "政治面貌",
    "毕业院校", "工作单位", "工作内容", "职务", "项目名称", "项目责任", "学位", 
    "毕业时间", "工作时间", "项目时间",
]


class GlobalPointer(nn.Module):
    def __init__(self, input_dim: int, heads: int, head_size: int = 64, rope: bool = True):
        super().__init__()
        self.heads = heads
        self.head_size = head_size
        self.rope = rope
        self.dense = nn.Linear(input_dim, heads * head_size * 2)

    def forward(self, inputs: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        inputs = self.dense(inputs)
        batch_size, seq_len, _ = inputs.shape
        inputs = inputs.view(batch_size, seq_len, self.heads, self.head_size * 2)
        qw, kw = inputs[..., : self.head_size], inputs[..., self.head_size :]
        if self.rope:
            pos = torch.arange(seq_len, device=inputs.device).unsqueeze(-1)
            indices = torch.arange(0, self.head_size, 2, dtype=torch.float32, device=inputs.device)
            sin_inp = torch.sin(pos / 10000 ** (indices / self.head_size))
            cos_inp = torch.cos(pos / 10000 ** (indices / self.head_size))
            sin_inp = torch.repeat_interleave(sin_inp, 2, dim=-1)
            cos_inp = torch.repeat_interleave(cos_inp, 2, dim=-1)
            sin_inp = sin_inp.unsqueeze(0).unsqueeze(2)
            cos_inp = cos_inp.unsqueeze(0).unsqueeze(2)
            qw2 = torch.stack([-qw[..., 1::2], qw[..., ::2]], dim=-1).reshape_as(qw)
            qw = qw * cos_inp + qw2 * sin_inp
            kw2 = torch.stack([-kw[..., 1::2], kw[..., ::2]], dim=-1).reshape_as(kw)
            kw = kw * cos_inp + kw2 * sin_inp
        logits = torch.einsum("bmhd,bnhd->bhmn", qw, kw)
        if mask is not None:
            mask = mask.unsqueeze(1).unsqueeze(1)
            logits = logits - (1 - mask) * 1e12
            logits = logits - (1 - mask.transpose(-1, -2)) * 1e12
        mask_tri = torch.tril(torch.ones_like(logits), diagonal=-1)
        logits = logits - mask_tri * 1e12
        return logits / self.head_size**0.5


class ResumeNerModel(BertPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.bert = BertModel(config)
        self.global_pointer = GlobalPointer(config.hidden_size, NerConfig.num_classes, head_size=64, rope=True)

        self.post_init()

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None) -> torch.Tensor:
        outputs = self.bert(input_ids, attention_mask=attention_mask)
        return self.global_pointer(outputs.last_hidden_state, mask=attention_mask)


class NerInferenceEngine:
    def __init__(self, config: NerConfig | None = None):
        try:
            self.config = config or NerConfig()
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
            print("\n" + "="*50, flush=True)
            print("🛠️ 正在初始化 NER 引擎...", flush=True)
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name, 
                local_files_only=True
            )
            self.model = ResumeNerModel.from_pretrained(
                self.config.model_name, 
                local_files_only=True,
                use_safetensors=False
            )
            
            print(f"📂 尝试寻找微调模型权重: {self.config.model_path}", flush=True)
            if self.config.model_path.exists():
                print("⏳ 找到模型文件，开始执行 torch.load 加载权重...", flush=True)
                state = torch.load(self.config.model_path, map_location=self.device)
                self.model.load_state_dict(state, strict=False)
                print("✅ 成功加载微调模型 best_model.pth ！", flush=True)
            else:
                raise FileNotFoundError(f"未找到 NER 模型权重文件: {self.config.model_path}")

            self.model.to(self.device)
            self.model.eval()
            print("✅ NER 引擎初始化完毕！\n" + "="*50, flush=True)

            self.schemas = {
                "教育经历": ["毕业时间", "毕业院校", "学位"],
                "工作经历": ["工作时间", "工作单位", "职务", "工作内容"],
                "项目经历": ["项目名称", "项目时间", "项目责任"],
            }
            self.basic_fields = ["姓名", "出生年月", "性别", "电话", "最高学历", "籍贯", "现居市县", "政治面貌"]

        except Exception as e:
            # 强制打印完整的错误堆栈，防止外层代码吞掉报错
            print("\n" + "!"*50, flush=True)
            print("❌ [致命错误] NER 引擎在 INIT (初始化) 阶段发生崩溃，具体原因如下：", flush=True)
            traceback.print_exc()
            print("!"*50 + "\n", flush=True)
            raise e

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
        except Exception:
            return ""
        return text

    def _predict_chunk(self, text_chunk: str, global_offset: int = 0) -> list[dict[str, Any]]:
        inputs = self.tokenizer(
            text_chunk,
            max_length=self.config.max_len,
            truncation=True,
            return_offsets_mapping=True,
            return_tensors="pt",
        )
        if "offset_mapping" not in inputs:
            raise ValueError("Tokenizer 中缺少 'offset_mapping'，请确保使用了 Fast Tokenizer。")
            
        input_ids = inputs["input_ids"].to(self.device)
        mask = inputs["attention_mask"].to(self.device)
        offset_mapping = inputs["offset_mapping"][0].cpu().numpy()

        with torch.no_grad():
            logits = self.model(input_ids, attention_mask=mask)[0].cpu().numpy()

        threshold = 0.0
        entities: list[dict[str, Any]] = []
        for idx, cat in enumerate(NerCategories):
            matrix = logits[idx]
            start_idxs, end_idxs = np.where(matrix > threshold)
            for start, end in zip(start_idxs, end_idxs):
                if start > end:
                    continue
                char_start = offset_mapping[start][0]
                char_end = offset_mapping[end][1]
                if char_start == 0 and char_end == 0:
                    continue
                value = text_chunk[char_start:char_end]
                if value:
                    entities.append({
                        "category": cat,
                        "value": value,
                        "start": char_start + global_offset,
                        "end": char_end + global_offset,
                    })
        return entities

    def _rebuild_nested_json(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        entities = sorted(entities, key=lambda x: x["start"])
        result: dict[str, Any] = {"项目经历": [], "教育经历": [], "工作经历": []}
        for field in self.basic_fields:
            vals = [e["value"] for e in entities if e["category"] == field]
            if vals:
                result[field] = vals[0]

        def build_list(block_key: str, block_fields: list[str]) -> None:
            current_group: dict[str, Any] = {}
            for entity in entities:
                cat = entity["category"]
                if cat in block_fields:
                    if cat in current_group:
                        result[block_key].append(current_group)
                        current_group = {}
                    current_group[cat] = entity["value"]
            if current_group:
                result[block_key].append(current_group)

        build_list("教育经历", self.schemas["教育经历"])
        build_list("工作经历", self.schemas["工作经历"])
        build_list("项目经历", self.schemas["项目经历"])
        return {k: v for k, v in result.items() if v}

    def predict_text(self, text: str) -> dict[str, Any]:
        if not text:
            return {}
        all_entities: list[dict[str, Any]] = []
        start = 0
        while start < len(text):
            end = min(start + self.config.chunk_size, len(text))
            chunk = text[start:end]
            all_entities.extend(self._predict_chunk(chunk, global_offset=start))
            if end == len(text):
                break
            start += self.config.chunk_size - self.config.overlap

        unique_entities: list[dict[str, Any]] = []
        seen = set()
        for entity in all_entities:
            identifier = f"{entity['category']}-{entity['start']}-{entity['end']}"
            if identifier not in seen:
                seen.add(identifier)
                unique_entities.append(entity)
        return self._rebuild_nested_json(unique_entities)

    def predict_pdf(self, pdf_path: str) -> dict[str, Any]:
        try:
            print(f"🔍 正在执行 NER 解析，目标文件: {pdf_path}", flush=True)
            return self.predict_text(self.extract_text_from_pdf(pdf_path))
        except Exception as e:
            print("\n" + "!"*50, flush=True)
            print(f"❌ [致命错误] NER 引擎在解析 PDF ({pdf_path}) 阶段发生崩溃：", flush=True)
            traceback.print_exc()
            print("!"*50 + "\n", flush=True)
            raise e


_ENGINE: NerInferenceEngine | None = None

def get_ner_engine() -> NerInferenceEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = NerInferenceEngine()
    return _ENGINE