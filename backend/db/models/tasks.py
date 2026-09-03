from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base

if TYPE_CHECKING:
    from db.models.evidences import TaskEvidence
    from db.models.users import User


class Task(Base):
    """Represent task data and behavior."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    work_catalog_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("work_catalog_items.id"), index=True
    )
    catalog_code_snapshot: Mapped[str | None] = mapped_column(String(40))
    catalog_name_snapshot: Mapped[str | None] = mapped_column(String(500))
    expected_output_snapshot: Mapped[str | None] = mapped_column(String(500))
    complexity_group_snapshot: Mapped[str | None] = mapped_column(String(10))
    catalog_score_snapshot: Mapped[float | None] = mapped_column(Float)
    conversion_factor_snapshot: Mapped[float | None] = mapped_column(Float)
    assignment_authority: Mapped[str | None] = mapped_column(String(80))
    position_scope: Mapped[str | None] = mapped_column(String(255))
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    document_type: Mapped[str] = mapped_column(String(1), default="C")
    status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED")
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    assignments: Mapped[list["TaskAssignment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    evidences: Mapped[list["TaskEvidence"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    work_catalog_item = relationship("WorkCatalogItem")


class TaskAssignment(Base):
    """Represent task assignment data and behavior."""

    __tablename__ = "task_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0)
    self_score: Mapped[float | None] = mapped_column(Float)
    leader_score: Mapped[float | None] = mapped_column(Float)
    final_score: Mapped[float | None] = mapped_column(Float)
    quality_percent: Mapped[float] = mapped_column(Float, default=100)
    major_error_count: Mapped[int] = mapped_column(Integer, default=0)
    late_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(30), default="NOT_STARTED", nullable=False, index=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    quality_status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False
    )
    objective_quality_exception: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    quality_exception_reason: Mapped[str | None] = mapped_column(Text)
    quality_exception_supporting_record: Mapped[str | None] = mapped_column(Text)
    quality_exception_verified_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id")
    )
    quality_exception_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    objective_delay_exception: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    delay_exception_reason: Mapped[str | None] = mapped_column(Text)
    delay_exception_supporting_record: Mapped[str | None] = mapped_column(Text)
    delay_exception_verified_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id")
    )
    delay_exception_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    result_verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    result_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    result_verification_note: Mapped[str | None] = mapped_column(Text)

    task: Mapped["Task"] = relationship(back_populates="assignments")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
