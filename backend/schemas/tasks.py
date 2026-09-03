from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskAssignmentIn(BaseModel):
    """Represent task assignment in data and behavior."""

    user_id: int
    progress_percent: float = 0


class TaskCreate(BaseModel):
    """Represent task create data and behavior."""

    title: str
    description: str | None = None
    creator_id: int | None = None
    department_id: int | None = None
    work_catalog_item_id: int | None = None
    deadline: datetime | None = None
    priority: str = "MEDIUM"
    assigned_user_ids: list[int] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    """Represent task update data and behavior."""

    title: str | None = None
    description: str | None = None
    work_catalog_item_id: int | None = None
    deadline: datetime | None = None
    priority: str | None = None


class TaskStatusUpdate(BaseModel):
    """Represent task status update data and behavior."""

    status: str
    progress_percent: float | None = None


class AssignmentVerification(BaseModel):
    """Validate a human product review and deterministic deduction inputs."""

    quality_status: str
    major_error_count: int = 0
    late_count: int = 0
    verification_note: str | None = None
    quality_exception_reason: str | None = None
    quality_exception_supporting_record: str | None = None
    delay_exception_reason: str | None = None
    delay_exception_supporting_record: str | None = None


class TaskOut(BaseModel):
    """Represent task out data and behavior."""

    id: int
    title: str
    description: str | None = None
    creator_id: int | None = None
    department_id: int | None = None
    work_catalog_item_id: int | None = None
    work_catalog_code: str | None = None
    deadline: datetime | None = None
    catalog_name: str | None = None
    expected_output: str | None = None
    complexity_group: str | None = None
    catalog_score: float | None = None
    conversion_factor: float | None = None
    assignment_authority: str | None = None
    position_scope: str | None = None
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
    assignees: list[dict] = Field(default_factory=list)
    evidence_count: int = 0

    model_config = ConfigDict(from_attributes=True)
