"""JD expert config database model."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import DECIMAL, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JdExpertConfig(Base):
    __tablename__ = "jd_expert_configs"

    jd_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    expert_id: Mapped[int] = mapped_column(
        ForeignKey("experts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    weight: Mapped[Decimal] = mapped_column(DECIMAL(5, 4), default=Decimal("1.0000"), nullable=False)

    job_description: Mapped["JobDescription"] = relationship(back_populates="jd_expert_configs")  # noqa: F821
    expert: Mapped["Expert"] = relationship(back_populates="jd_expert_configs")  # noqa: F821
