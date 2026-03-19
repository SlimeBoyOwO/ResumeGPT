"""Resume extraction pipeline: NER first, LLM fallback with PII masking."""

from __future__ import annotations

import json
from typing import Any

from app.services.llm_resume_extractor import parse_resume_with_llm
from app.services.ner_engine import get_ner_engine


class ExtractionError(RuntimeError):
    def __init__(self, message: str, partial_data: dict[str, Any] | None = None):
        super().__init__(message)
        self.partial_data = partial_data


def _mask_pii(text: str, name: str | None, phone: str | None) -> str:
    masked = text
    if name:
        masked = masked.replace(name, "张三")
    if phone:
        masked = masked.replace(phone, "10086114514")
    return masked


# 新增：将 LLM 提取出的假 PII 换回真实的姓名和电话
def _unmask_pii(data: dict[str, Any], orig_name: str | None, orig_phone: str | None) -> dict[str, Any]:
    # 转为字符串做全量替换最安全（防止假名出现在"自我介绍"等其他字段里）
    data_str = json.dumps(data, ensure_ascii=False)
    if orig_name:
        data_str = data_str.replace("张三", orig_name)
    if orig_phone:
        data_str = data_str.replace("10086114514", orig_phone)
    return json.loads(data_str)


def extract_resume_data(pdf_path: str) -> tuple[dict[str, Any], str]:
    engine = get_ner_engine()
    text = engine.extract_text_from_pdf(pdf_path)
    if not text:
        raise ExtractionError("Empty PDF text.")

    # 1. 强制提取 NER 结果（作为辅助信息以及提取真实 PII）
    ner_result = engine.predict_text(text)
    orig_name = ner_result.get("姓名")
    orig_phone = ner_result.get("电话")

    # 2. 对原文进行 PII 脱敏
    masked_text = _mask_pii(text, orig_name, orig_phone)
    
    # 注意：传给 LLM 的 NER 辅助字典也必须脱敏！否则 LLM 直接看到真名了
    masked_ner_result = {}
    if ner_result:
        ner_str = json.dumps(ner_result, ensure_ascii=False)
        masked_ner_str = _mask_pii(ner_str, orig_name, orig_phone)
        masked_ner_result = json.loads(masked_ner_str)

    # 3. 强制使用 LLM 提取，并将脱敏后的 NER 结果作为提示传入
    try:
        llm_result = parse_resume_with_llm(masked_text, ner_hint=masked_ner_result)
    except Exception as exc:
        raise ExtractionError("LLM extraction failed.", partial_data=ner_result) from exc

    # 4. 把 LLM 返回的 JSON 里的假名、假手机号替换回真实数据
    final_result = _unmask_pii(llm_result, orig_name, orig_phone)

    # 返回最终结果，标识源为 'llm_with_ner'
    return final_result, "llm_with_ner"