from core.deps import get_current_user
from core.organization import SPECIALIST_ROLE, UBND_AUTHORITY_ROLE
from core.permissions import (
    can_assign_task,
    can_manage_task,
    can_verify_task_result,
    get_visible_users,
    is_admin,
)
from db.database import get_db
from db.models.evidences import TaskEvidence
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from fastapi import APIRouter, Depends, HTTPException
from schemas.tasks import (
    AssignmentVerification,
    TaskCreate,
    TaskStatusUpdate,
    TaskUpdate,
)
from services.audit_service import record_audit_event
from services.task_service import (
    TaskService,
    effective_task_status,
    effective_task_status_expression,
)
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
        "work_catalog_code": task.catalog_code_snapshot,
        "deadline": task.deadline,
        "catalog_name": task.catalog_name_snapshot,
        "expected_output": task.expected_output_snapshot,
        "complexity_group": task.complexity_group_snapshot,
        "catalog_score": task.catalog_score_snapshot,
        "conversion_factor": task.conversion_factor_snapshot,
        "assignment_authority": task.assignment_authority,
        "position_scope": task.position_scope,
        "status": effective_task_status(task),
        "priority": task.priority,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "assignees": [
            {
                "assignment_id": item.id,
                "user_id": item.user_id,
                "full_name": item.user.full_name if item.user else None,
                "progress_percent": item.progress_percent,
                "status": item.status,
                "submitted_at": item.submitted_at,
                "self_score": item.self_score,
                "leader_score": item.leader_score,
                "final_score": item.final_score,
                "quality_status": item.quality_status,
                "major_error_count": item.major_error_count,
                "late_count": item.late_count,
            }
            for item in task.assignments
        ],
        "evidence_count": len(task.evidences),
    }


def apply_task_visibility(query, current_user: User):
    """Limit task queries to organization, unit, or assignee scope."""

    if is_admin(current_user) or current_user.organization_role == UBND_AUTHORITY_ROLE:
        return query
    visible_users = get_visible_users(
        current_user,
        query.session.query(User).all(),
    )
    visible_user_ids = [user.id for user in visible_users]
    return query.join(TaskAssignment).filter(
        TaskAssignment.user_id.in_(visible_user_ids)
    )


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
        query = query.filter(effective_task_status_expression() == status)

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

    status_expression = effective_task_status_expression().label("effective_status")
    query = apply_task_visibility(
        db.query(status_expression, func.count(func.distinct(Task.id))),
        current_user,
    )

    counts = dict(query.group_by(status_expression).all())
    total = sum(counts.values())
    return {
        "total": total,
        "by_status": counts,
        "completed": counts.get("VERIFIED", 0),
        "overdue": counts.get("OVERDUE", 0),
    }


@router.post("")
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a task after validating every requested assignee."""

    if is_admin(current_user) or current_user.organization_role == SPECIALIST_ROLE:
        raise HTTPException(
            status_code=403, detail="Chuyên viên không có quyền giao nhiệm vụ."
        )

    # Verify can_assign_to for all assignees
    targets: list[User] = []
    for uid in payload.assigned_user_ids:
        target = db.get(User, uid)
        if not target or not can_assign_task(current_user, target):
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
        return task_to_dict(TaskService(db).create(payload, current_user.id))
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
        return task_to_dict(TaskService(db).update(task, payload, current_user.id))
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

    record_audit_event(
        db,
        actor_id=current_user.id,
        action="TASK_DELETED",
        entity_type="TASK",
        entity_id=task.id,
        before={"title": task.title, "catalog_code": task.catalog_code_snapshot},
    )
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

    assignment = next(
        (item for item in task.assignments if item.user_id == current_user.id), None
    )
    if assignment is None:
        raise HTTPException(
            status_code=403, detail="Chỉ người thực hiện được cập nhật tiến độ của mình."
        )
    allowed_statuses = {"NOT_STARTED", "IN_PROGRESS", "SUBMITTED"}
    if payload.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái hợp lệ: NOT_STARTED, IN_PROGRESS hoặc SUBMITTED.",
        )
    before = {"status": assignment.status, "progress_percent": assignment.progress_percent}
    assignment.status = payload.status
    if payload.progress_percent is not None:
        assignment.progress_percent = payload.progress_percent
    if payload.status == "SUBMITTED":
        from datetime import datetime

        if not any(item.assignment_id == assignment.id for item in task.evidences):
            raise HTTPException(status_code=400, detail="Cần nộp ít nhất một sản phẩm đầu ra.")
        assignment.submitted_at = datetime.utcnow()
        assignment.progress_percent = 100
    statuses = {item.status for item in task.assignments}
    task.status = "SUBMITTED" if statuses == {"SUBMITTED"} else (
        "IN_PROGRESS" if statuses - {"NOT_STARTED"} else "NOT_STARTED"
    )
    record_audit_event(
        db,
        actor_id=current_user.id,
        action="ASSIGNMENT_STATUS_UPDATED",
        entity_type="TASK_ASSIGNMENT",
        entity_id=assignment.id,
        before=before,
        after={"status": assignment.status, "progress_percent": assignment.progress_percent},
    )
    db.commit()
    db.refresh(task)
    return task_to_dict(task)


@router.patch("/{task_id}/assignments/{user_id}/verify")
def verify_assignment_result(
    task_id: int,
    user_id: int,
    payload: AssignmentVerification,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Verify a submitted output using deterministic quality and delay inputs."""

    target_user = db.get(User, user_id)
    if target_user is None or not can_verify_task_result(current_user, target_user):
        raise HTTPException(status_code=403, detail="Không có quyền đánh giá sản phẩm này.")
    if payload.quality_status not in {"PASS", "FAIL"}:
        raise HTTPException(status_code=400, detail="Kết quả chất lượng phải là PASS hoặc FAIL.")
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
    if assignment.status != "SUBMITTED":
        raise HTTPException(status_code=400, detail="Sản phẩm chưa ở trạng thái chờ xác minh.")
    has_verified_output = db.query(TaskEvidence.id).filter(
        TaskEvidence.assignment_id == assignment.id,
        TaskEvidence.verification_status == "VERIFIED",
    ).first()
    if has_verified_output is None:
        raise HTTPException(status_code=409, detail="Chưa có sản phẩm đầu ra được xác minh.")
    from datetime import datetime

    before = {"status": assignment.status, "quality_status": assignment.quality_status}
    assignment.status = "VERIFIED"
    assignment.quality_status = payload.quality_status
    assignment.major_error_count = payload.major_error_count
    assignment.late_count = payload.late_count
    assignment.result_verified_by = current_user.id
    assignment.result_verified_at = datetime.utcnow()
    assignment.result_verification_note = payload.verification_note
    assignment.objective_quality_exception = False
    assignment.quality_exception_reason = None
    assignment.quality_exception_supporting_record = None
    assignment.quality_exception_verified_by = None
    assignment.quality_exception_verified_at = None
    assignment.objective_delay_exception = False
    assignment.delay_exception_reason = None
    assignment.delay_exception_supporting_record = None
    assignment.delay_exception_verified_by = None
    assignment.delay_exception_verified_at = None
    if payload.quality_exception_reason or payload.quality_exception_supporting_record:
        if not payload.quality_exception_reason or not payload.quality_exception_supporting_record:
            raise HTTPException(status_code=400, detail="Ngoại lệ chất lượng cần đủ lý do và hồ sơ.")
        assignment.objective_quality_exception = True
        assignment.quality_exception_reason = payload.quality_exception_reason
        assignment.quality_exception_supporting_record = payload.quality_exception_supporting_record
        assignment.quality_exception_verified_by = current_user.id
        assignment.quality_exception_verified_at = datetime.utcnow()
    if payload.delay_exception_reason or payload.delay_exception_supporting_record:
        if not payload.delay_exception_reason or not payload.delay_exception_supporting_record:
            raise HTTPException(status_code=400, detail="Ngoại lệ tiến độ cần đủ lý do và hồ sơ.")
        assignment.objective_delay_exception = True
        assignment.delay_exception_reason = payload.delay_exception_reason
        assignment.delay_exception_supporting_record = payload.delay_exception_supporting_record
        assignment.delay_exception_verified_by = current_user.id
        assignment.delay_exception_verified_at = datetime.utcnow()
    if all(item.status == "VERIFIED" for item in assignment.task.assignments):
        assignment.task.status = "VERIFIED"
        assignment.task.completed_at = datetime.utcnow()
    record_audit_event(
        db,
        actor_id=current_user.id,
        action="PRODUCT_VERIFIED",
        entity_type="TASK_ASSIGNMENT",
        entity_id=assignment.id,
        before=before,
        after={"status": assignment.status, "quality_status": assignment.quality_status,
               "major_error_count": assignment.major_error_count, "late_count": assignment.late_count},
        reason=payload.verification_note,
    )
    db.commit()
    db.refresh(assignment.task)
    return task_to_dict(assignment.task)
