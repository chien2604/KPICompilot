from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskAssignmentIn(BaseModel):
    user_id: int
    progress_percent: float = 0


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    creator_id: int | None = None
    department_id: int | None = None
    deadline: datetime | None = None
    weight: float = 1
    document_type: str = "C"
    status: str = "NOT_STARTED"
    priority: str = "MEDIUM"
    assigned_user_ids: list[int] = []


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    weight: float | None = None
    document_type: str | None = None
    status: str | None = None
    priority: str | None = None
    progress_percent: float | None = None


class TaskStatusUpdate(BaseModel):
    status: str
    progress_percent: float | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    creator_id: int | None = None
    department_id: int | None = None
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
