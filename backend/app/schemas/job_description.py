"""Job description schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class JobDescriptionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    description: str = Field(..., min_length=1)
    status: Literal["open", "closed"] = "open"
    auto_select_experts: bool
    expected_hires: int = Field(10, ge=1)
    workflow_graph: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_workflow(self) -> "JobDescriptionCreate":
        if self.auto_select_experts:
            if self.workflow_graph:
                raise ValueError("workflow_graph must be empty when auto_select_experts is true.")
            return self

        if not self.workflow_graph:
            raise ValueError("workflow_graph must be provided in manual mode.")

        if "nodes" not in self.workflow_graph or "edges" not in self.workflow_graph:
            raise ValueError("workflow_graph must contain 'nodes' and 'edges'.")
        
        return self


class JobDescriptionResponse(BaseModel):
    id: int
    enterprise_id: int
    title: str
    department: str | None = None
    description: str
    vector_id: str | None = None
    status: str
    expected_hires: int
    created_at: datetime
    workflow_mode: Literal["manual", "auto_pending"]
    workflow_graph: dict[str, Any] | None = None


class JobDescriptionListResponse(BaseModel):
    total: int
    items: list[JobDescriptionResponse]
