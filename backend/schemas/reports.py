from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportGenerateIn(BaseModel):
    """Validate report generation parameters."""

    report_type: str = "WEEKLY"
    period: str
    department_id: int | None = None
    created_by: int | None = None


class ReportContentUpdateIn(BaseModel):
    """Payload cho tính năng Edit báo cáo. Sửa trực tiếp toàn bộ Markdown."""

    content: str


class ReportOut(BaseModel):
    """Serialize a generated report."""

    id: int
    report_type: str
    period: str
    department_id: int | None = None
    content: str
    content_html: str | None = None
    summary_json: dict
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
