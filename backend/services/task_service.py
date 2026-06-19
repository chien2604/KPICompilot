from sqlalchemy.orm import Session

from db.models.tasks import Task, TaskAssignment
from schemas.tasks import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: TaskCreate) -> Task:
        task = Task(**payload.model_dump(exclude={"assigned_user_ids"}))
        self.db.add(task)
        self.db.flush()
        for user_id in payload.assigned_user_ids:
            self.db.add(TaskAssignment(task_id=task.id, user_id=user_id, progress_percent=0))
        self.db.commit()
        self.db.refresh(task)
        return task

    def update(self, task: Task, payload: TaskUpdate) -> Task:
        data = payload.model_dump(exclude_unset=True)
        progress = data.pop("progress_percent", None)
        for key, value in data.items():
            setattr(task, key, value)
        if progress is not None:
            for assignment in task.assignments:
                assignment.progress_percent = progress
        self.db.commit()
        self.db.refresh(task)
        return task
