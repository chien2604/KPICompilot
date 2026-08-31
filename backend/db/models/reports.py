from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class Report(Base):
    """Represent report data and behavior."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(30), default="WEEKLY")
    period: Mapped[str] = mapped_column(String(30), nullable=False)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )

    # content: HTML fragment sinh trực tiếp từ LLM theo report_generator_prompt.txt.
    # Đây là NGUỒN DỮ LIỆU CHÍNH — Web hiển thị trực tiếp, PDF render từ HTML này,
    # DOCX cũng convert từ HTML này (xem ai_layer/report_docx_renderer.py).
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # summary_json: dữ liệu thống kê đầu vào đã gửi cho LLM (audit trail / debug),
    # KHÔNG dùng để render — chỉ để biết LLM đã thấy số liệu gì khi sinh báo cáo.
    # Có thêm field "_source" ("llm" | "llm_retry" | "fallback") để biết nguồn gốc nội dung.
    summary_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
