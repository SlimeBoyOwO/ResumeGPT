"""Match record database model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MatchRecord(Base):
    __tablename__ = "match_records"
    __table_args__ = (
        UniqueConstraint("jd_id", "resume_id", name="uk_jd_resume"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    jd_id: Mapped[int] = mapped_column(ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    workflow_status: Mapped[str] = mapped_column(
        String(30),
        default="rough_matching",
        nullable=False,
        comment="rough_matching / agent_evaluating / completed / failed",
    )
    vector_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    comprehensive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ability_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    job_description: Mapped["JobDescription"] = relationship(back_populates="match_records")  # noqa: F821
    resume: Mapped["Resume"] = relationship(back_populates="match_records")  # noqa: F821
    expert_evaluations: Mapped[list["ExpertEvaluation"]] = relationship(  # noqa: F821
        back_populates="match_record",
        cascade="all, delete-orphan",
    )
