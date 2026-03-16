"""Resume database model."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="Stored filename (UUID)")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="Original filename")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="File storage path")
    file_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="File type (pdf/docx/jpg etc.)")
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        comment="Parsing status: pending, parsing, parsed, failed",
    )
    ner_extracted_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="NER extracted data as JSON",
    )
    vector_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Vector DB ID",
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="resumes")  # noqa: F821
    match_records: Mapped[list["MatchRecord"]] = relationship(  # noqa: F821
        back_populates="resume",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, original_filename={self.original_filename}, status={self.status})>"
