from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportGenerateIn(BaseModel):
    report_type: str = "WEEKLY"
    period: str
    department_id: int | None = None
    created_by: int | None = None


class ReportOut(BaseModel):
    id: int
    report_type: str
    period: str
    department_id: int | None = None
    content: str
    summary_json: dict
    created_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
