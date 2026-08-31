from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field


class KPIScoreOut(BaseModel):
    """Represent k p i score out data and behavior."""

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
    """Represent k p i criterion out data and behavior."""

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


class KPIAssessmentInputUpdate(BaseModel):
    """Validate manual inputs required by Decision 283 and Decree 335."""

    common_scores: dict[str, float] = Field(default_factory=dict)
    management_metrics: dict[str, float] = Field(default_factory=dict)
