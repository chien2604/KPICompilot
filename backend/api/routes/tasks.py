from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.evidences import TaskEvidence
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from core.deps import get_current_user
from core.permissions import get_user_level, can_assign_to, is_admin
from schemas.tasks import TaskCreate, TaskStatusUpdate, TaskUpdate
from services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def task_to_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "creator_id": task.creator_id,
        "department_id": task.department_id,
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
            }
            for item in task.assignments
        ],
        "evidence_count": len(task.evidences),
    }


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
    level = get_user_level(current_user)
    
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
        
    # Phân quyền xem
    if is_admin(current_user):
        # Admin xem tất cả, có thể filter theo bất kỳ tiêu chí nào
        if assigned_user_id:
            query = query.join(TaskAssignment).filter(TaskAssignment.user_id == assigned_user_id)
        if department_id:
            query = query.filter(Task.department_id == department_id)
    elif level == 5:
        # Chuyên viên chỉ xem task của mình
        query = query.join(TaskAssignment).filter(TaskAssignment.user_id == current_user.id)
    else:
        # Lãnh đạo
        if assigned_user_id:
            query = query.join(TaskAssignment).filter(TaskAssignment.user_id == assigned_user_id)
        if level in [3, 4]:
            # Trưởng/Phó phòng xem task phòng mình
            query = query.filter(Task.department_id == current_user.department_id)
        else:
            # Giám đốc xem tất cả, có thể filter theo department_id
            if department_id:
                query = query.filter(Task.department_id == department_id)
                
    if creator_id:
        query = query.filter(Task.creator_id == creator_id)
    if month:
        year, month_value = month.split("-")
        query = query.filter(extract("year", Task.created_at) == int(year), extract("month", Task.created_at) == int(month_value))
    return [task_to_dict(task) for task in query.order_by(Task.deadline.asc().nullslast()).all()]


@router.get("/stats")
def task_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    level = get_user_level(current_user)
    query = db.query(Task.status, func.count(Task.id))
    
    if not is_admin(current_user):
        if level == 5:
            query = query.join(TaskAssignment).filter(TaskAssignment.user_id == current_user.id)
        elif level in [3, 4]:
            query = query.filter(Task.department_id == current_user.department_id)
        
    counts = dict(query.group_by(Task.status).all())
    total = sum(counts.values())
    return {"total": total, "by_status": counts, "completed": counts.get("COMPLETED", 0), "overdue": counts.get("OVERDUE", 0)}


@router.post("")
def create_task(payload: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    level = get_user_level(current_user)
    if not is_admin(current_user) and level == 5:
        raise HTTPException(status_code=403, detail="Chuyên viên không có quyền tạo nhiệm vụ")
    
    # Verify can_assign_to for all assignees
    for uid in payload.assigned_user_ids:
        target = db.get(User, uid)
        if not target or not can_assign_to(current_user, target):
            raise HTTPException(status_code=403, detail=f"Không có quyền giao việc cho user {uid}")
            
    payload.creator_id = current_user.id
    if not is_admin(current_user) and level in [3, 4] and not payload.department_id:
        payload.department_id = current_user.department_id
        
    return task_to_dict(TaskService(db).create(payload))


@router.get("/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")
        
    level = get_user_level(current_user)
    if not is_admin(current_user):
        if level == 5:
            if current_user.id not in [a.user_id for a in task.assignments]:
                raise HTTPException(status_code=403, detail="Bạn không có quyền xem nhiệm vụ này")
        elif level in [3, 4]:
            if task.department_id != current_user.department_id:
                raise HTTPException(status_code=403, detail="Bạn không có quyền xem nhiệm vụ phòng khác")
            
    return task_to_dict(task)


@router.patch("/{task_id}")
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")
        
    level = get_user_level(current_user)
    if not is_admin(current_user):
        if level == 5:
            raise HTTPException(status_code=403, detail="Chuyên viên không có quyền sửa nhiệm vụ")
        if level in [3, 4] and task.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Bạn không có quyền sửa nhiệm vụ phòng khác")
        
    return task_to_dict(TaskService(db).update(task, payload))


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")
        
    level = get_user_level(current_user)
    if not is_admin(current_user):
        if level == 5:
            raise HTTPException(status_code=403, detail="Chuyên viên không có quyền xóa nhiệm vụ")
        if level in [3, 4] and task.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Bạn không có quyền xóa nhiệm vụ phòng khác")
        
    db.delete(task)
    db.commit()
    return {"ok": True}


@router.patch("/{task_id}/status")
def update_status(task_id: int, payload: TaskStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")
        
    level = get_user_level(current_user)
    is_assignee = current_user.id in [a.user_id for a in task.assignments]

    if not is_admin(current_user):
        if level == 5 and not is_assignee:
            raise HTTPException(status_code=403, detail="Chỉ người thực hiện mới được cập nhật tiến độ")
        if level in [3, 4] and task.department_id != current_user.department_id and not is_assignee:
            raise HTTPException(status_code=403, detail="Bạn không có quyền cập nhật tiến độ nhiệm vụ phòng khác")

    task.status = payload.status
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
    if not target_user or not can_assign_to(current_user, target_user):
        raise HTTPException(status_code=403, detail="Bạn không có quyền chấm điểm người này")

    assignment = db.query(TaskAssignment).filter(
        TaskAssignment.task_id == task_id,
        TaskAssignment.user_id == user_id,
    ).first()
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
