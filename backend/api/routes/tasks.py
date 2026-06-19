from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.evidences import TaskEvidence
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
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
    month: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if department_id:
        query = query.filter(Task.department_id == department_id)
    if assigned_user_id:
        query = query.join(TaskAssignment).filter(TaskAssignment.user_id == assigned_user_id)
    if month:
        year, month_value = month.split("-")
        query = query.filter(extract("year", Task.created_at) == int(year), extract("month", Task.created_at) == int(month_value))
    return [task_to_dict(task) for task in query.order_by(Task.deadline.asc().nullslast()).all()]


@router.get("/stats")
def task_stats(db: Session = Depends(get_db)) -> dict:
    counts = dict(db.query(Task.status, func.count(Task.id)).group_by(Task.status).all())
    total = sum(counts.values())
    return {"total": total, "by_status": counts, "completed": counts.get("COMPLETED", 0), "overdue": counts.get("OVERDUE", 0)}


@router.post("")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> dict:
    return task_to_dict(TaskService(db).create(payload))


@router.get("/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")
    return task_to_dict(task)


@router.patch("/{task_id}")
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")
    return task_to_dict(TaskService(db).update(task, payload))


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")
    db.delete(task)
    db.commit()
    return {"ok": True}


@router.patch("/{task_id}/status")
def update_status(task_id: int, payload: TaskStatusUpdate, db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")
    task.status = payload.status
    if payload.progress_percent is not None:
        for assignment in task.assignments:
            assignment.progress_percent = payload.progress_percent
    db.commit()
    db.refresh(task)
    return task_to_dict(task)
