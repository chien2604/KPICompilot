from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    weight: float = 1
    document_type: str = "C"
    status: str = "NOT_STARTED"
    priority: str = "MEDIUM"
    assigned_user_ids: list[int] = []


class TaskUpdate(BaseModel):
    """Represent task update data and behavior."""

    title: str | None = None
    description: str | None = None
    work_catalog_item_id: int | None = None
    deadline: datetime | None = None
    weight: float | None = None
    document_type: str | None = None
    status: str | None = None
    priority: str | None = None
    progress_percent: float | None = None


class TaskStatusUpdate(BaseModel):
    """Represent task status update data and behavior."""

    status: str
    progress_percent: float | None = None


class TaskQualityUpdate(BaseModel):
    """Validate reviewer quality and Decree 335 deduction inputs."""

    quality_percent: float
    major_error_count: int = 0
    late_count: int = 0


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
    weight: float
    document_type: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
    assignees: list[dict] = []
    evidence_count: int = 0

    model_config = ConfigDict(from_attributes=True)
