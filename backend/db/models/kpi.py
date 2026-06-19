from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class KPITemplate(Base):
    __tablename__ = "kpi_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_role: Mapped[str] = mapped_column(String(80), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, default=100)

    criteria: Mapped[list["KPICriterion"]] = relationship(back_populates="template", cascade="all, delete-orphan")


class KPICriterion(Base):
    __tablename__ = "kpi_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("kpi_templates.id", ondelete="CASCADE"), index=True)
    group_code: Mapped[str] = mapped_column(String(20), nullable=False)
    group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    criterion_code: Mapped[str] = mapped_column(String(50), nullable=False)
    criterion_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    calculation_rule_text: Mapped[str | None] = mapped_column(Text)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped["KPITemplate"] = relationship(back_populates="criteria")


class DocumentTypeRule(Base):
    __tablename__ = "document_type_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(1), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    scoring_rule_text: Mapped[str] = mapped_column(Text, nullable=False)


class KPIScore(Base):
    __tablename__ = "kpi_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    period_month: Mapped[str] = mapped_column(String(7), index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("kpi_templates.id"))
    total_score: Mapped[float] = mapped_column(Float, default=0)
    classification: Mapped[str] = mapped_column(String(100), nullable=False)
    breakdown_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    ai_explanation: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
