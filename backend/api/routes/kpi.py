from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from db.database import get_db
from db.models.departments import Department
from db.models.kpi import KPICriterion, KPIScore, KPITemplate
from db.models.tasks import Task
from db.models.users import User
from services.kpi_engine import KPIEngine

router = APIRouter(prefix="/kpi", tags=["kpi"])


@router.get("/dashboard")
def dashboard(month: str = "2026-06", db: Session = Depends(get_db)) -> dict:
    users = db.query(User).filter(User.is_active.is_(True)).count()
    avg = db.query(func.avg(KPIScore.total_score)).filter(KPIScore.period_month == month).scalar() or 0
    task_counts = dict(db.query(Task.status, func.count(Task.id)).group_by(Task.status).all())
    top = _ranking_query(db, month, None, desc=True, limit=5)
    low = _ranking_query(db, month, None, desc=False, limit=5)
    return {
        "total_users": users,
        "avg_kpi": round(float(avg), 1),
        "task_completed": task_counts.get("COMPLETED", 0),
        "task_total": sum(task_counts.values()),
        "task_overdue": task_counts.get("OVERDUE", 0),
        "task_status": task_counts,
        "top_users": top,
        "low_users": low,
    }


@router.get("/heatmap")
def heatmap(month: str = "2026-06", db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(Department.id, Department.name, func.avg(KPIScore.total_score), func.count(User.id))
        .join(User, User.department_id == Department.id)
        .join(KPIScore, KPIScore.user_id == User.id)
        .filter(KPIScore.period_month == month)
        .group_by(Department.id, Department.name)
        .order_by(Department.id)
        .all()
    )
    return [{"department_id": r[0], "department": r[1], "avg_kpi": round(float(r[2] or 0), 1), "user_count": r[3]} for r in rows]


@router.get("/users/{user_id}/profile")
def user_profile(user_id: int, month: str = "2026-06", db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ")
    score = db.query(KPIScore).filter(KPIScore.user_id == user_id, KPIScore.period_month == month).order_by(KPIScore.created_at.desc()).first()
    tasks = db.query(Task).join(Task.assignments).filter_by(user_id=user_id).limit(20).all()
    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "position_title": user.position_title,
            "department": user.department.name if user.department else None,
            "kpi_role_template": user.kpi_role_template,
        },
        "score": _score_dict(score) if score else None,
        "tasks": [{"id": t.id, "title": t.title, "status": t.status, "deadline": t.deadline, "document_type": t.document_type} for t in tasks],
    }


@router.get("/users/{user_id}/score")
def user_score(user_id: int, month: str = "2026-06", db: Session = Depends(get_db)) -> dict:
    score = db.query(KPIScore).filter(KPIScore.user_id == user_id, KPIScore.period_month == month).order_by(KPIScore.created_at.desc()).first()
    if not score:
        score = KPIEngine(db).recompute_and_save(user_id, month)
    return _score_dict(score)


@router.post("/users/{user_id}/score/recompute")
def recompute(user_id: int, month: str = "2026-06", db: Session = Depends(get_db)) -> dict:
    return _score_dict(KPIEngine(db).recompute_and_save(user_id, month))


@router.get("/criteria")
def criteria(role_template: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    query = db.query(KPICriterion).join(KPITemplate)
    if role_template:
        query = query.filter(KPITemplate.code == role_template)
    return [
        {
            "id": row.id,
            "template_id": row.template_id,
            "group_code": row.group_code,
            "group_name": row.group_name,
            "criterion_code": row.criterion_code,
            "criterion_name": row.criterion_name,
            "description": row.description,
            "calculation_rule_text": row.calculation_rule_text,
            "max_score": row.max_score,
            "sort_order": row.sort_order,
        }
        for row in query.order_by(KPICriterion.sort_order).all()
    ]


@router.get("/ranking")
def ranking(month: str = "2026-06", department_id: int | None = None, db: Session = Depends(get_db)) -> list[dict]:
    return _ranking_query(db, month, department_id, desc=True, limit=100)


def _ranking_query(db: Session, month: str, department_id: int | None, desc: bool, limit: int) -> list[dict]:
    query = db.query(User, KPIScore).join(KPIScore, KPIScore.user_id == User.id).filter(KPIScore.period_month == month)
    if department_id:
        query = query.filter(User.department_id == department_id)
    order = KPIScore.total_score.desc() if desc else KPIScore.total_score.asc()
    return [
        {
            "user_id": user.id,
            "full_name": user.full_name,
            "department": user.department.name if user.department else None,
            "score": score.total_score,
            "classification": score.classification,
            "risk_level": score.risk_level,
        }
        for user, score in query.order_by(order).limit(limit).all()
    ]


def _score_dict(score: KPIScore) -> dict:
    return {
        "id": score.id,
        "user_id": score.user_id,
        "period_month": score.period_month,
        "template_id": score.template_id,
        "total_score": score.total_score,
        "classification": score.classification,
        "breakdown_json": score.breakdown_json,
        "ai_explanation": score.ai_explanation,
        "risk_level": score.risk_level,
        "created_at": score.created_at,
    }
