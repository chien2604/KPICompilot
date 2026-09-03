from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base

if TYPE_CHECKING:
    from db.models.tasks import Task


class TaskEvidence(Base):
    """Represent task evidence data and behavior."""

    __tablename__ = "task_evidences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey("task_assignments.id", ondelete="CASCADE"), index=True
    )
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    result_type: Mapped[str] = mapped_column(
        String(30), default="PRIMARY_OUTPUT", nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(30), default="FILE_UPLOAD", nullable=False
    )
    source_system: Mapped[str | None] = mapped_column(String(255))
    source_record_id: Mapped[str | None] = mapped_column(String(255))
    document_number: Mapped[str | None] = mapped_column(String(100))
    issued_date: Mapped[datetime | None] = mapped_column(DateTime)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ai_analysis_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    file_hash_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(100))
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    ai_relevance_score: Mapped[float | None] = mapped_column(Float)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_missing_points: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="UPLOADED")
    verification_status: Mapped[str] = mapped_column(
        String(30), default="DRAFT", nullable=False, index=True
    )
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    verification_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped["Task"] = relationship(back_populates="evidences")
