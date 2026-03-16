"""Resume extraction pipeline: NER first, LLM fallback with PII masking."""

from __future__ import annotations

from typing import Any

from app.services.llm_resume_extractor import parse_resume_with_llm
from app.services.ner_engine import get_ner_engine


class ExtractionError(RuntimeError):
    def __init__(self, message: str, partial_data: dict[str, Any] | None = None):
        super().__init__(message)
        self.partial_data = partial_data


def _is_insufficient(data: dict[str, Any]) -> bool:
    if not data:
        return True
    if not data.get("教育经历"):
        return True
    if not data.get("工作经历"):
        return True
    if not data.get("项目经历"):
        return True
    return False


def _mask_pii(text: str, name: str | None, phone: str | None) -> str:
    masked = text
    if name:
        masked = masked.replace(name, "张三")
    if phone:
        masked = masked.replace(phone, "XXXXXXX")
    return masked


def extract_resume_data(pdf_path: str) -> tuple[dict[str, Any], str]:
    engine = get_ner_engine()
    text = engine.extract_text_from_pdf(pdf_path)
    if not text:
        raise ExtractionError("Empty PDF text.")

    ner_result = engine.predict_text(text)
    if not _is_insufficient(ner_result):
        return ner_result, "ner"

    masked_text = _mask_pii(text, ner_result.get("姓名"), ner_result.get("电话"))
    try:
        llm_result = parse_resume_with_llm(masked_text)
    except Exception as exc:
        raise ExtractionError("LLM extraction failed.", partial_data=ner_result) from exc

    return llm_result, "llm"
