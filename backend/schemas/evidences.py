from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class EvidenceReferenceCreate(BaseModel):
    """Validate a product represented by an external system link or record."""

    task_id: int
    assignment_id: int
    url: AnyHttpUrl
    title: str
    result_type: str = "PRIMARY_OUTPUT"
    source_system: str | None = None
    source_record_id: str | None = None
    document_number: str | None = None
    metadata: dict = Field(default_factory=dict)


class EvidenceVerificationUpdate(BaseModel):
    """Validate a human decision for one submitted product."""

    verification_status: str
    note: str | None = None


class EvidenceOut(BaseModel):
    """Represent evidence out data and behavior."""

    id: int
    task_id: int
    assignment_id: int | None = None
    uploaded_by: int
    file_name: str
    file_type: str | None = None
    file_path: str
    extracted_text: str | None = None
    ai_relevance_score: float | None = None
    ai_summary: str | None = None
    ai_missing_points: str | None = None
    status: str
    result_type: str = "PRIMARY_OUTPUT"
    source_type: str = "FILE_UPLOAD"
    source_system: str | None = None
    source_record_id: str | None = None
    document_number: str | None = None
    metadata: dict = Field(default_factory=dict)
    file_hash_sha256: str | None = None
    verification_status: str = "DRAFT"
    verified_by: int | None = None
    verified_at: datetime | None = None
    verification_note: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceAnalysisOut(BaseModel):
    """Represent evidence analysis out data and behavior."""

    evidence_id: int
    relevance_score: float | None = None
    summary: str | None = None
    missing_points: list[str] = Field(default_factory=list)
    status: str
