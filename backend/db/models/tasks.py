from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    document_type: Mapped[str] = mapped_column(String(1), default="C")
    status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED")
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments: Mapped[list["TaskAssignment"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    evidences: Mapped[list["TaskEvidence"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskAssignment(Base):
    __tablename__ = "task_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0)
    self_score: Mapped[float | None] = mapped_column(Float)
    leader_score: Mapped[float | None] = mapped_column(Float)
    final_score: Mapped[float | None] = mapped_column(Float)

    task: Mapped["Task"] = relationship(back_populates="assignments")
    user: Mapped["User"] = relationship()
