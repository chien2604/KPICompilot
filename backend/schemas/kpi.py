from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KPIScoreOut(BaseModel):
    id: int | None = None
    user_id: int
    period_month: str
    template_id: int | None = None
    total_score: float
    classification: str
    breakdown_json: dict
    ai_explanation: str | None = None
    risk_level: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class KPICriterionOut(BaseModel):
    id: int
    template_id: int
    group_code: str
    group_name: str
    criterion_code: str
    criterion_name: str
    description: str | None = None
    calculation_rule_text: str | None = None
    max_score: float
    sort_order: int

    model_config = ConfigDict(from_attributes=True)
