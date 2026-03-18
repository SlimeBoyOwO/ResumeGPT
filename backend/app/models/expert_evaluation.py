"""Expert evaluation database model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ExpertEvaluation(Base):
    __tablename__ = "expert_evaluations"
    __table_args__ = (
        UniqueConstraint("match_record_id", "node_id", name="uk_match_expert_node"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_record_id: Mapped[int] = mapped_column(
        ForeignKey("match_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(String(50), nullable=False)
    expert_id: Mapped[int] = mapped_column(ForeignKey("experts.id", ondelete="CASCADE"), nullable=False)
    agent_status: Mapped[str] = mapped_column(String(20), default="processing", nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    match_record: Mapped["MatchRecord"] = relationship(back_populates="expert_evaluations")  # noqa: F821
    expert: Mapped["Expert"] = relationship(back_populates="expert_evaluations")  # noqa: F821
