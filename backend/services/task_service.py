from datetime import datetime

from db.models.kpi import WorkCatalogItem
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from schemas.tasks import TaskCreate, TaskUpdate
from sqlalchemy import case
from sqlalchemy.orm import Session

from services.audit_service import record_audit_event
from services.work_catalog_service import is_catalog_item_assignable

OPEN_TASK_STATUSES = ("NOT_STARTED", "IN_PROGRESS")


def effective_task_status_expression():
    """Return a SQL expression that derives overdue status from the deadline."""

    return case(
        (
            Task.deadline < datetime.utcnow(),
            case(
                (Task.status.in_(OPEN_TASK_STATUSES), "OVERDUE"),
                else_=Task.status,
            ),
        ),
        else_=Task.status,
    )


def effective_task_status(task: Task) -> str:
    """Return the current operational status without mutating historical data."""

    if (
        task.deadline is not None
        and task.deadline < datetime.utcnow()
        and task.status in OPEN_TASK_STATUSES
    ):
        return "OVERDUE"
    return task.status


class TaskService:
    """Represent task service data and behavior."""

    def __init__(self, db: Session) -> None:
        """Initialize the task service."""

        self.db = db

    def create(self, payload: TaskCreate, actor_id: int) -> Task:
        """Create the operation."""

        task_data = payload.model_dump(exclude={"assigned_user_ids"})
        if payload.work_catalog_item_id is not None:
            catalog_item = self.db.get(WorkCatalogItem, payload.work_catalog_item_id)
            if catalog_item is None or not catalog_item.is_active:
                raise ValueError("Mã công việc không tồn tại hoặc đã ngừng áp dụng.")
            task_data.update(
                catalog_code_snapshot=catalog_item.code,
                catalog_name_snapshot=catalog_item.name,
                expected_output_snapshot=catalog_item.output,
                complexity_group_snapshot=catalog_item.complexity_group,
                catalog_score_snapshot=catalog_item.conversion_score,
                conversion_factor_snapshot=catalog_item.conversion_factor,
                weight=catalog_item.conversion_factor,
            )
        else:
            raise ValueError("Nhiệm vụ chính thức phải chọn mã trong danh mục công việc.")
        actor = self.db.get(User, actor_id)
        targets = self._load_and_validate_targets(
            payload.assigned_user_ids,
            catalog_item,
        )
        task_data["assignment_authority"] = (
            actor.organization_role if actor is not None else None
        )
        task_data["position_scope"] = ", ".join(
            sorted({target.primary_position_code for target in targets})
        )[:255]
        task = Task(**task_data)
        self.db.add(task)
        self.db.flush()
        for user_id in payload.assigned_user_ids:
            self.db.add(
                TaskAssignment(task_id=task.id, user_id=user_id, progress_percent=0)
            )
        record_audit_event(
            self.db,
            actor_id=actor_id,
            action="TASK_ASSIGNED",
            entity_type="TASK",
            entity_id=task.id,
            after={
                "assignee_ids": payload.assigned_user_ids,
                "catalog_code": task.catalog_code_snapshot,
            },
        )
        self.db.commit()
        self.db.refresh(task)
        return task

    def update(self, task: Task, payload: TaskUpdate, actor_id: int) -> Task:
        """Update task details and preserve an auditable before/after snapshot."""

        before = self._task_snapshot(task)
        data = payload.model_dump(exclude_unset=True)
        if "work_catalog_item_id" in data and data["work_catalog_item_id"] is None:
            raise ValueError("Nhiệm vụ chính thức không được bỏ mã danh mục công việc.")
        for key, value in data.items():
            setattr(task, key, value)
        if task.work_catalog_item_id is not None:
            catalog_item = self.db.get(WorkCatalogItem, task.work_catalog_item_id)
            if catalog_item is None or not catalog_item.is_active:
                raise ValueError("Mã công việc không tồn tại hoặc đã ngừng áp dụng.")
            self._load_and_validate_targets(
                [assignment.user_id for assignment in task.assignments],
                catalog_item,
            )
            task.catalog_code_snapshot = catalog_item.code
            task.catalog_name_snapshot = catalog_item.name
            task.expected_output_snapshot = catalog_item.output
            task.complexity_group_snapshot = catalog_item.complexity_group
            task.catalog_score_snapshot = catalog_item.conversion_score
            task.conversion_factor_snapshot = catalog_item.conversion_factor
            task.weight = catalog_item.conversion_factor
        after = self._task_snapshot(task)
        record_audit_event(
            self.db,
            actor_id=actor_id,
            action="TASK_UPDATED",
            entity_type="TASK",
            entity_id=task.id,
            before=before,
            after=after,
        )
        if before["deadline"] != after["deadline"]:
            record_audit_event(
                self.db,
                actor_id=actor_id,
                action="TASK_DEADLINE_CHANGED",
                entity_type="TASK",
                entity_id=task.id,
                before={"deadline": before["deadline"]},
                after={"deadline": after["deadline"]},
            )
        self.db.commit()
        self.db.refresh(task)
        return task

    def _load_and_validate_targets(
        self,
        target_ids: list[int],
        catalog_item: WorkCatalogItem,
    ) -> list[User]:
        """Load unique active targets and validate catalog applicability."""

        targets = self.db.query(User).filter(User.id.in_(target_ids)).all()
        if len(targets) != len(target_ids):
            raise ValueError("Danh sách người nhận có tài khoản không hợp lệ hoặc bị trùng.")
        invalid_targets = [
            target.full_name
            for target in targets
            if not is_catalog_item_assignable(catalog_item, target)
        ]
        if invalid_targets:
            raise ValueError(
                "Mã công việc không phù hợp với vị trí/lĩnh vực của: "
                + ", ".join(sorted(invalid_targets))
            )
        return targets

    @staticmethod
    def _task_snapshot(task: Task) -> dict:
        """Return stable task fields suitable for JSON audit storage."""

        return {
            "title": task.title,
            "description": task.description,
            "work_catalog_item_id": task.work_catalog_item_id,
            "catalog_code": task.catalog_code_snapshot,
            "assignment_authority": task.assignment_authority,
            "position_scope": task.position_scope,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "priority": task.priority,
        }
