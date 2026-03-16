"""Expert evaluation schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ExpertEvaluationResponse(BaseModel):
    id: int
    match_record_id: int
    expert_id: int
    agent_status: str
    score: float | None = None
    analysis_content: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
