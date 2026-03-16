"""Match record schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MatchRecordResponse(BaseModel):
    id: int
    jd_id: int
    resume_id: int
    workflow_status: str
    vector_similarity: float | None = None
    final_score: float | None = None
    comprehensive_summary: str | None = None
    ability_summary: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
