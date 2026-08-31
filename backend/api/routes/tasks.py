from core.deps import get_current_user
from core.organization import LEADERSHIP_ROLE, SPECIALIST_ROLE
from core.permissions import can_assign_to, can_manage_task, can_score, is_admin
from db.database import get_db
from db.models.kpi import WorkCatalogItem
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from fastapi import APIRouter, Depends, HTTPException, Query
from schemas.tasks import TaskCreate, TaskQualityUpdate, TaskStatusUpdate, TaskUpdate
from services.task_service import TaskService
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

router = APIRouter(prefix="/tasks", tags=["tasks"])


def task_to_dict(task: Task) -> dict:
    """Serialize a task with assignments and evidence count."""

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "creator_id": task.creator_id,
        "department_id": task.department_id,
        "work_catalog_item_id": task.work_catalog_item_id,
        "work_catalog_code": (
            task.work_catalog_item.code if task.work_catalog_item_id else None
        ),
        "deadline": task.deadline,
        "weight": task.weight,
        "document_type": task.document_type,
        "status": task.status,
        "priority": task.priority,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "assignees": [
            {
                "user_id": item.user_id,
                "full_name": item.user.full_name if item.user else None,
                "progress_percent": item.progress_percent,
                "self_score": item.self_score,
                "leader_score": item.leader_score,
                "final_score": item.final_score,
                "quality_percent": item.quality_percent,
                "major_error_count": item.major_error_count,
                "late_count": item.late_count,
            }
            for item in task.assignments
        ],
        "evidence_count": len(task.evidences),
    }


def apply_task_visibility(query, current_user: User):
    """Limit task queries to organization, unit, or assignee scope."""

    if is_admin(current_user) or current_user.organization_role == LEADERSHIP_ROLE:
        return query
    if current_user.organization_role != SPECIALIST_ROLE:
        return query.filter(Task.department_id == current_user.department_id)
    return query.join(TaskAssignment).filter(TaskAssignment.user_id == current_user.id)


@router.get("")
def list_tasks(
    status: str | None = None,
    department_id: int | None = None,
    assigned_user_id: int | None = None,
    creator_id: int | None = None,
    month: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List tasks within organization, unit manager, or assignee scope."""

    query = apply_task_visibility(db.query(Task), current_user)
    if status:
        query = query.filter(Task.status == status)

    if assigned_user_id:
        query = query.join(TaskAssignment).filter(
            TaskAssignment.user_id == assigned_user_id
        )
    if department_id:
        query = query.filter(Task.department_id == department_id)

    if creator_id:
        query = query.filter(Task.creator_id == creator_id)
    if month:
        year, month_value = month.split("-")
        query = query.filter(
            extract("year", Task.created_at) == int(year),
            extract("month", Task.created_at) == int(month_value),
        )
    return [
        task_to_dict(task)
        for task in query.order_by(Task.deadline.asc().nullslast()).all()
    ]


@router.get("/stats")
def task_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    """Return task status counts within the current user's scope."""

    query = apply_task_visibility(
        db.query(Task.status, func.count(func.distinct(Task.id))), current_user
    )

    counts = dict(query.group_by(Task.status).all())
    total = sum(counts.values())
    return {
        "total": total,
        "by_status": counts,
        "completed": counts.get("COMPLETED", 0),
        "overdue": counts.get("OVERDUE", 0),
    }


@router.post("")
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a task after validating every requested assignee."""

    if not is_admin(current_user) and current_user.organization_role == SPECIALIST_ROLE:
        raise HTTPException(
            status_code=403, detail="Chuyên viên không có quyền giao nhiệm vụ."
        )

    # Verify can_assign_to for all assignees
    targets: list[User] = []
    for uid in payload.assigned_user_ids:
        target = db.get(User, uid)
        if not target or not can_assign_to(current_user, target):
            raise HTTPException(
                status_code=403, detail=f"Không có quyền giao việc cho user {uid}"
            )
        targets.append(target)

    if not targets:
        raise HTTPException(status_code=400, detail="Cần chọn ít nhất một người thực hiện.")

    payload.creator_id = current_user.id
    target_department_ids = {target.department_id for target in targets}
    payload.department_id = (
        next(iter(target_department_ids)) if len(target_department_ids) == 1 else None
    )
    try:
        return task_to_dict(TaskService(db).create(payload))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/{task_id}")
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return one task when it is visible to the current user."""

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")

    visible_task = apply_task_visibility(db.query(Task), current_user).filter(
        Task.id == task_id
    ).first()
    if visible_task is None:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem nhiệm vụ này.")

    return task_to_dict(task)


@router.patch("/{task_id}")
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update a task when managed by the current assigner."""

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")

    if not can_manage_task(current_user, task.creator_id):
        raise HTTPException(status_code=403, detail="Chỉ người giao việc được sửa nhiệm vụ.")
    try:
        return task_to_dict(TaskService(db).update(task, payload))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a task when managed by the current assigner."""

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")

    if not can_manage_task(current_user, task.creator_id):
        raise HTTPException(status_code=403, detail="Chỉ người giao việc được xóa nhiệm vụ.")

    db.delete(task)
    db.commit()
    return {"ok": True}


@router.patch("/{task_id}/status")
def update_status(
    task_id: int,
    payload: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update task status and assignment progress within the allowed scope."""

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")

    is_assignee = current_user.id in [a.user_id for a in task.assignments]
    if not is_assignee and not can_manage_task(current_user, task.creator_id):
        raise HTTPException(
            status_code=403, detail="Chỉ người thực hiện hoặc người giao việc được cập nhật."
        )

    task.status = payload.status
    if payload.status == "COMPLETED" and task.completed_at is None:
        from datetime import datetime

        task.completed_at = datetime.utcnow()
    elif payload.status != "COMPLETED":
        task.completed_at = None
    if payload.progress_percent is not None:
        for assignment in task.assignments:
            assignment.progress_percent = payload.progress_percent
    db.commit()
    db.refresh(task)
    return task_to_dict(task)


@router.patch("/{task_id}/assignments/{user_id}/score")
def score_assignment(
    task_id: int,
    user_id: int,
    leader_score: float = Query(..., ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Cấp trên chấm điểm cho một người được giao nhiệm vụ."""
    target_user = db.get(User, user_id)
    if not target_user or not can_score(current_user, target_user):
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền chấm điểm người này"
        )

    assignment = (
        db.query(TaskAssignment)
        .filter(
            TaskAssignment.task_id == task_id,
            TaskAssignment.user_id == user_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy phân công nhiệm vụ")
    assignment.leader_score = leader_score
    assignment.final_score = (
        (assignment.self_score or 0) * 0.3 + leader_score * 0.7
        if assignment.self_score is not None
        else leader_score
    )
    db.commit()
    db.refresh(assignment.task)
    return task_to_dict(assignment.task)


@router.patch("/{task_id}/assignments/{user_id}/quality")
def update_assignment_quality(
    task_id: int,
    user_id: int,
    payload: TaskQualityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Store reviewer quality and statutory deduction counts for one product."""

    target_user = db.get(User, user_id)
    if target_user is None or not can_score(current_user, target_user):
        raise HTTPException(status_code=403, detail="Không có quyền đánh giá sản phẩm này.")
    if not 0 <= payload.quality_percent <= 100:
        raise HTTPException(status_code=400, detail="Chất lượng phải từ 0 đến 100%.")
    if payload.major_error_count < 0 or payload.late_count < 0:
        raise HTTPException(status_code=400, detail="Số lần vi phạm không được âm.")
    assignment = (
        db.query(TaskAssignment)
        .filter(
            TaskAssignment.task_id == task_id,
            TaskAssignment.user_id == user_id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phân công nhiệm vụ.")
    assignment.quality_percent = payload.quality_percent
    assignment.major_error_count = payload.major_error_count
    assignment.late_count = payload.late_count
    db.commit()
    db.refresh(assignment.task)
    return task_to_dict(assignment.task)
