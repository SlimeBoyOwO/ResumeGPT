"""简历相关 Pydantic Schemas"""

from datetime import datetime

from pydantic import BaseModel


class ResumeResponse(BaseModel):
    id: int
    user_id: int
    original_filename: str
    file_size: int
    file_type: str
    status: str
    score: float | None = None
    analysis_summary: str | None = None
    best_match_position: str | None = None
    uploaded_at: datetime
    # 关联的用户名（管理员查看用）
    username: str | None = None

    model_config = {"from_attributes": True}


class ResumeListResponse(BaseModel):
    total: int
    items: list[ResumeResponse]
