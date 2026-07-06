from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from db.database import get_db
from db.models.departments import Department
from db.models.kpi import KPICriterion, KPIScore, KPITemplate
from db.models.tasks import Task
from db.models.users import User
from services.kpi_engine import KPIEngine
from core.deps import get_current_user
from core.permissions import get_user_level

router = APIRouter(prefix="/kpi", tags=["kpi"])


@router.get("/dashboard")
def dashboard(month: str = "2026-06", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    level = get_user_level(current_user)
    dept_id = current_user.department_id

    task_q = db.query(Task.status, func.count(Task.id))
    avg_q = db.query(func.avg(KPIScore.total_score)).filter(KPIScore.period_month == month)

    if level <= 2:
        scope = "org_wide"
        users = db.query(User).filter(User.is_active.is_(True)).count()
        task_counts = dict(task_q.group_by(Task.status).all())
        avg = avg_q.scalar() or 0
        top = _ranking_query(db, month, None, desc=True, limit=5)
        low = _ranking_query(db, month, None, desc=False, limit=5)

    elif level in [3, 4]:
        scope = "department"
        users = db.query(User).filter(User.is_active.is_(True), User.department_id == dept_id).count()
        task_counts = dict(task_q.filter(Task.department_id == dept_id).group_by(Task.status).all())
        avg = avg_q.join(User, User.id == KPIScore.user_id).filter(User.department_id == dept_id).scalar() or 0
        top = _ranking_query(db, month, dept_id, desc=True, limit=5)
        low = _ranking_query(db, month, dept_id, desc=False, limit=5)

    else:
        scope = "personal"
        users = 1
        from db.models.tasks import TaskAssignment
        task_counts = dict(
            task_q.join(TaskAssignment, TaskAssignment.task_id == Task.id)
            .filter(TaskAssignment.user_id == current_user.id)
            .group_by(Task.status).all()
        )
        avg = avg_q.filter(KPIScore.user_id == current_user.id).scalar() or 0
        top = []
        low = []

    return {
        "scope": scope,
        "total_users": users,
        "avg_kpi": round(float(avg), 1),
        "task_completed": task_counts.get("COMPLETED", 0),
        "task_total": sum(task_counts.values()),
        "task_overdue": task_counts.get("OVERDUE", 0),
        "task_status": task_counts,
        "top_users": top,
        "low_users": low,
        "department_name": current_user.department.name if current_user.department else None,
    }


@router.get("/heatmap")
def heatmap(month: str = "2026-06", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    if get_user_level(current_user) > 2:
        raise HTTPException(status_code=403, detail="Chỉ lãnh đạo Sở mới có quyền xem bản đồ nhiệt toàn cơ quan.")
        
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
def user_profile(user_id: int, month: str = "2026-06", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ")
        
    level = get_user_level(current_user)
    if level == 5 and user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem hồ sơ người này")
    if level in [3, 4] and user.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem hồ sơ người của phòng khác")
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
def user_score(user_id: int, month: str = "2026-06", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    user = db.get(User, user_id)
    level = get_user_level(current_user)
    if level == 5 and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem điểm người này")
    if level in [3, 4] and user and user.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem điểm người của phòng khác")

    score = db.query(KPIScore).filter(KPIScore.user_id == user_id, KPIScore.period_month == month).order_by(KPIScore.created_at.desc()).first()
    if not score:
        score = KPIEngine(db).recompute_and_save(user_id, month)
    return _score_dict(score)


@router.post("/users/{user_id}/score/recompute")
def recompute(user_id: int, month: str = "2026-06", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    user = db.get(User, user_id)
    level = get_user_level(current_user)
    if level == 5 and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền chấm lại điểm người này")
    if level in [3, 4] and user and user.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền chấm lại điểm người của phòng khác")
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
def ranking(month: str = "2026-06", department_id: int | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    level = get_user_level(current_user)
    if level == 5:
        raise HTTPException(status_code=403, detail="Chuyên viên không có quyền xem xếp hạng")
    if level in [3, 4]:
        department_id = current_user.department_id
        
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
