"""Expert database model."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Expert(Base):
    __tablename__ = "experts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    expert_evaluations: Mapped[list["ExpertEvaluation"]] = relationship(  # noqa: F821
        back_populates="expert",
        cascade="all, delete-orphan",
    )
