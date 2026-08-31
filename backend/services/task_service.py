from datetime import datetime

from db.models.kpi import WorkCatalogItem
from db.models.tasks import Task, TaskAssignment
from schemas.tasks import TaskCreate, TaskUpdate
from sqlalchemy.orm import Session


class TaskService:
    """Represent task service data and behavior."""

    def __init__(self, db: Session) -> None:
        """Initialize the task service."""

        self.db = db

    def create(self, payload: TaskCreate) -> Task:
        """Create the operation."""

        task_data = payload.model_dump(exclude={"assigned_user_ids"})
        if payload.work_catalog_item_id is not None:
            catalog_item = self.db.get(WorkCatalogItem, payload.work_catalog_item_id)
            if catalog_item is None or not catalog_item.is_active:
                raise ValueError("Mã công việc không tồn tại hoặc đã ngừng áp dụng.")
            task_data["weight"] = catalog_item.conversion_factor
        task = Task(**task_data)
        self.db.add(task)
        self.db.flush()
        for user_id in payload.assigned_user_ids:
            self.db.add(
                TaskAssignment(task_id=task.id, user_id=user_id, progress_percent=0)
            )
        self.db.commit()
        self.db.refresh(task)
        return task

    def update(self, task: Task, payload: TaskUpdate) -> Task:
        """Update the operation."""

        data = payload.model_dump(exclude_unset=True)
        progress = data.pop("progress_percent", None)
        for key, value in data.items():
            setattr(task, key, value)
        if task.work_catalog_item_id is not None:
            catalog_item = self.db.get(WorkCatalogItem, task.work_catalog_item_id)
            if catalog_item is None or not catalog_item.is_active:
                raise ValueError("Mã công việc không tồn tại hoặc đã ngừng áp dụng.")
            task.weight = catalog_item.conversion_factor
        if task.status == "COMPLETED" and task.completed_at is None:
            task.completed_at = datetime.utcnow()
        elif task.status != "COMPLETED":
            task.completed_at = None
        if progress is not None:
            for assignment in task.assignments:
                assignment.progress_percent = progress
        self.db.commit()
        self.db.refresh(task)
        return task
