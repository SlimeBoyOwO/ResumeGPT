"""Expert schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ExpertResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    system_prompt: str
    created_at: datetime

    model_config = {"from_attributes": True}
