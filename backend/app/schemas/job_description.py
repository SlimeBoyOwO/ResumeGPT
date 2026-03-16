"""Job description schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobDescriptionResponse(BaseModel):
    id: int
    enterprise_id: int
    title: str
    department: str | None = None
    description: str
    vector_id: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
