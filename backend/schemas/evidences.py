from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceOut(BaseModel):
    """Represent evidence out data and behavior."""

    id: int
    task_id: int
    uploaded_by: int
    file_name: str
    file_type: str | None = None
    file_path: str
    extracted_text: str | None = None
    ai_relevance_score: float | None = None
    ai_summary: str | None = None
    ai_missing_points: str | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceAnalysisOut(BaseModel):
    """Represent evidence analysis out data and behavior."""

    evidence_id: int
    relevance_score: float | None = None
    summary: str | None = None
    missing_points: list[str] = []
    status: str
