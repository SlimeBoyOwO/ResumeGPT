"""Resume-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ResumeResponse(BaseModel):
    id: int
    user_id: int
    original_filename: str
    file_type: str
    status: str
    ner_extracted_data: dict[str, Any] | None = None
    vector_id: str | None = None
    uploaded_at: datetime
    username: str | None = None

    model_config = {"from_attributes": True}


class ResumeListResponse(BaseModel):
    total: int
    items: list[ResumeResponse]
