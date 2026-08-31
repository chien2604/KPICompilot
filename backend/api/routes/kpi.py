from datetime import datetime

from core.deps import get_current_user
from core.organization import (
    LEADERSHIP_ROLE,
    OUT_OF_SCOPE_ROLE,
    SPECIALIST_ROLE,
    UNIT_DEPUTY_ROLE,
    UNIT_HEAD_ROLE,
    USER_ROLE,
)
from core.permissions import can_score, can_view_user, get_user_level, is_admin
from db.database import get_db
from db.models.departments import Department
from db.models.kpi import (
    KPIAssessmentInput,
    KPICriterion,
    KPIScore,
    KPITemplate,
    WorkCatalogItem,
)
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from fastapi import APIRouter, Depends, HTTPException
from services.kpi_engine import KPIEngine
from schemas.kpi import KPIAssessmentInputUpdate
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

router = APIRouter(prefix="/kpi", tags=["kpi"])


def resolve_period_month(month: str | None) -> str:
    """Return a validated month or the current calendar month."""

    period_month = month or datetime.now().strftime("%Y-%m")
    try:
        datetime.strptime(period_month, "%Y-%m")
    except ValueError as error:
        raise HTTPException(
            status_code=400, detail="Kỳ KPI phải có định dạng YYYY-MM."
        ) from error
    return period_month


def apply_task_scope(query, current_user: User):
    """Apply organization, unit, or personal task scope to a query."""

    if is_admin(current_user) or current_user.organization_role == LEADERSHIP_ROLE:
        return query
    if current_user.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}:
        return query.filter(Task.department_id == current_user.department_id)
    return query.join(TaskAssignment, TaskAssignment.task_id == Task.id).filter(
        TaskAssignment.user_id == current_user.id
    )


def apply_score_scope(query, current_user: User):
    """Apply organization, unit, or personal KPI score scope to a query."""

    if is_admin(current_user) or current_user.organization_role == LEADERSHIP_ROLE:
        return query
    if current_user.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}:
        return query.join(User, User.id == KPIScore.user_id).filter(
            User.department_id == current_user.department_id
        )
    return query.filter(KPIScore.user_id == current_user.id)


@router.get("/dashboard")
def dashboard(
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return KPI and task summary data within the current user's scope."""

    period_month = resolve_period_month(month)
    user_query = database_session.query(User).filter(User.role == USER_ROLE)
    if not is_admin(current_user) and current_user.organization_role in {
        UNIT_HEAD_ROLE,
        UNIT_DEPUTY_ROLE,
    }:
        user_query = user_query.filter(User.department_id == current_user.department_id)
    elif not is_admin(current_user) and current_user.organization_role not in {
        LEADERSHIP_ROLE,
    }:
        user_query = user_query.filter(User.id == current_user.id)

    task_count_query = apply_task_scope(
        database_session.query(Task.status, func.count(func.distinct(Task.id))),
        current_user,
    )
    task_counts = dict(task_count_query.group_by(Task.status).all())

    average_query = apply_score_scope(
        database_session.query(func.avg(KPIScore.total_score)).filter(
            KPIScore.period_month == period_month
        ),
        current_user,
    )
    average_kpi = average_query.scalar()
    ranking_department_id = (
        None
        if is_admin(current_user) or current_user.organization_role == LEADERSHIP_ROLE
        else current_user.department_id
    )
    show_rankings = is_admin(current_user) or current_user.organization_role in {
        LEADERSHIP_ROLE,
        UNIT_HEAD_ROLE,
        UNIT_DEPUTY_ROLE,
    }

    return {
        "scope": (
            "organization"
            if is_admin(current_user) or current_user.organization_role == LEADERSHIP_ROLE
            else (
                "department"
                if current_user.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}
                else "personal"
            )
        ),
        "period_month": period_month,
        "total_users": user_query.count(),
        "kpi_eligible_users": user_query.filter(User.is_kpi_eligible.is_(True)).count(),
        "active_users": user_query.filter(User.is_active.is_(True)).count(),
        "avg_kpi": round(float(average_kpi), 1) if average_kpi is not None else None,
        "task_completed": task_counts.get("COMPLETED", 0),
        "task_total": sum(task_counts.values()),
        "task_overdue": task_counts.get("OVERDUE", 0),
        "task_status": task_counts,
        "top_users": _ranking_query(
            database_session,
            period_month,
            ranking_department_id,
            descending=True,
            limit=5,
        )
        if show_rankings
        else [],
        "low_users": _ranking_query(
            database_session,
            period_month,
            ranking_department_id,
            descending=False,
            limit=5,
        )
        if show_rankings
        else [],
        "kpi_trend": _kpi_trend(database_session, current_user),
        "department_name": current_user.department.name
        if current_user.department
        else None,
    }


@router.get("/heatmap")
def heatmap(
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Return all visible units, including units that do not yet have KPI scores."""

    period_month = resolve_period_month(month)
    department_query = database_session.query(Department).filter(
        Department.unit_type.in_(("LEADERSHIP", "UNIT"))
    )
    if not is_admin(current_user) and current_user.organization_role != LEADERSHIP_ROLE:
        department_query = department_query.filter(Department.id == current_user.department_id)
    result = []
    for department in department_query.order_by(Department.id).all():
        users = database_session.query(User).filter(User.department_id == department.id)
        eligible_ids = [user.id for user in users.filter(User.is_kpi_eligible.is_(True)).all()]
        average_kpi = None
        if eligible_ids:
            average_kpi = (
                database_session.query(func.avg(KPIScore.total_score))
                .filter(
                    KPIScore.period_month == period_month,
                    KPIScore.user_id.in_(eligible_ids),
                )
                .scalar()
            )
        result.append(
            {
                "department_id": department.id,
                "department": department.name,
                "avg_kpi": round(float(average_kpi), 1) if average_kpi is not None else None,
                "user_count": users.count(),
                "kpi_eligible_count": len(eligible_ids),
            }
        )
    return result


@router.get("/users/{user_id}/profile")
def user_profile(
    user_id: int,
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return personnel, KPI, and assigned-task information for an allowed user."""

    period_month = resolve_period_month(month)
    user = database_session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ.")
    if not can_view_user(current_user, user):
        raise HTTPException(
            status_code=403, detail="Không có quyền xem hồ sơ người này."
        )

    score = (
        database_session.query(KPIScore)
        .filter(KPIScore.user_id == user_id, KPIScore.period_month == period_month)
        .order_by(KPIScore.created_at.desc())
        .first()
    )
    tasks = (
        database_session.query(Task)
        .join(TaskAssignment, TaskAssignment.task_id == Task.id)
        .filter(TaskAssignment.user_id == user_id)
        .order_by(Task.deadline.desc())
        .limit(20)
        .all()
    )
    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "birth_year": user.birth_year,
            "date_of_birth": user.date_of_birth,
            "ethnicity": user.ethnicity,
            "party_joined_date": user.party_joined_date,
            "general_education": user.general_education,
            "professional_qualification": user.professional_qualification,
            "political_theory": user.political_theory,
            "role": user.role,
            "position_title": user.position_title,
            "department": user.department.name if user.department else None,
            "kpi_role_template": user.kpi_role_template,
            "organization_role": user.organization_role,
            "primary_position_code": user.primary_position_code,
            "personnel_type": user.personnel_type,
            "is_kpi_eligible": user.is_kpi_eligible,
            "source_work_area": user.source_work_area,
            "work_areas": [
                {"area_code": area.area_code, "area_name": area.area_name}
                for area in user.work_areas
            ],
            "is_active": user.is_active,
        },
        "score": _score_dict(score) if score else None,
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "deadline": task.deadline,
                "document_type": task.document_type,
            }
            for task in tasks
        ],
    }


@router.get("/users/{user_id}/score")
def user_score(
    user_id: int,
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return an existing KPI score without silently inventing or recomputing one."""

    period_month = resolve_period_month(month)
    user = database_session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ.")
    if not can_view_user(current_user, user):
        raise HTTPException(
            status_code=403, detail="Không có quyền xem điểm người này."
        )
    score = (
        database_session.query(KPIScore)
        .filter(KPIScore.user_id == user_id, KPIScore.period_month == period_month)
        .order_by(KPIScore.created_at.desc())
        .first()
    )
    if score is None:
        raise HTTPException(status_code=404, detail="Chưa có điểm KPI cho kỳ đã chọn.")
    return _score_dict(score)


@router.post("/users/{user_id}/score/recompute")
def recompute(
    user_id: int,
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Recompute KPI only when the current user may score the target user."""

    period_month = resolve_period_month(month)
    user = database_session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ.")
    if not is_admin(current_user) and not can_score(current_user, user):
        raise HTTPException(
            status_code=403, detail="Không có quyền chấm KPI người này."
        )
    try:
        return _score_dict(
            KPIEngine(database_session).recompute_and_save(user_id, period_month)
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/criteria")
def criteria(
    role_template: str | None = None,
    database_session: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List configured KPI criteria, optionally filtered by role template."""

    query = database_session.query(KPICriterion).join(KPITemplate)
    if role_template:
        query = query.filter(KPITemplate.code == role_template)
    return [
        {
            "id": criterion.id,
            "template_id": criterion.template_id,
            "group_code": criterion.group_code,
            "group_name": criterion.group_name,
            "criterion_code": criterion.criterion_code,
            "criterion_name": criterion.criterion_name,
            "description": criterion.description,
            "calculation_rule_text": criterion.calculation_rule_text,
            "max_score": criterion.max_score,
            "sort_order": criterion.sort_order,
        }
        for criterion in query.order_by(KPICriterion.sort_order).all()
    ]


@router.get("/work-catalog")
def work_catalog(
    user_id: int | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Return approved work codes matched to a visible person's role and work areas."""

    target = current_user if user_id is None else database_session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ.")
    if not can_view_user(current_user, target) and not can_score(current_user, target):
        raise HTTPException(status_code=403, detail="Không có quyền xem danh mục của người này.")
    if not target.is_kpi_eligible:
        return []
    filters = [WorkCatalogItem.catalog_scope == "COMMON"]
    if target.organization_role in {LEADERSHIP_ROLE, UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}:
        filters.append(WorkCatalogItem.catalog_scope == "LEADERSHIP")
    if target.department is not None:
        area_codes = [area.area_code for area in target.work_areas]
        area_filters = [WorkCatalogItem.code.like(f"{code}.%") for code in area_codes]
        department_filter = WorkCatalogItem.department_code == target.department.code
        if target.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE} or not area_filters:
            filters.append(department_filter)
        else:
            filters.append(department_filter & or_(*area_filters))
    rows = (
        database_session.query(WorkCatalogItem)
        .filter(WorkCatalogItem.is_active.is_(True), or_(*filters))
        .order_by(WorkCatalogItem.code)
        .all()
    )
    return [
        {
            "id": row.id,
            "code": row.code,
            "catalog_scope": row.catalog_scope,
            "department_code": row.department_code,
            "name": row.name,
            "details": row.details,
            "output": row.output,
            "complexity_group": row.complexity_group,
            "score_range": row.score_range,
            "conversion_score": row.conversion_score,
            "conversion_factor": row.conversion_factor,
        }
        for row in rows
    ]


@router.get("/users/{user_id}/assessment-inputs")
def get_assessment_inputs(
    user_id: int,
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return reviewer-entered common and management inputs for one month."""

    period_month = resolve_period_month(month)
    target = database_session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ.")
    if not can_view_user(current_user, target) and not can_score(current_user, target):
        raise HTTPException(status_code=403, detail="Không có quyền xem đầu vào đánh giá.")
    row = (
        database_session.query(KPIAssessmentInput)
        .filter(
            KPIAssessmentInput.user_id == user_id,
            KPIAssessmentInput.period_month == period_month,
        )
        .first()
    )
    return {
        "user_id": user_id,
        "period_month": period_month,
        "common_scores": row.common_scores_json if row else {},
        "management_metrics": row.management_metrics_json if row else {},
        "updated_at": row.updated_at if row else None,
    }


@router.put("/users/{user_id}/assessment-inputs")
def save_assessment_inputs(
    user_id: int,
    payload: KPIAssessmentInputUpdate,
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Validate and persist reviewer inputs without invoking an LLM."""

    period_month = resolve_period_month(month)
    target = database_session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ.")
    if not is_admin(current_user) and not can_score(current_user, target):
        raise HTTPException(status_code=403, detail="Không có quyền chấm cán bộ này.")
    valid_criteria = {
        criterion.criterion_code: criterion.max_score
        for criterion in database_session.query(KPICriterion)
        .join(KPITemplate)
        .filter(KPITemplate.code == target.kpi_role_template)
        .all()
    }
    for code, score in payload.common_scores.items():
        if code not in valid_criteria or not 0 <= score <= valid_criteria[code]:
            raise HTTPException(status_code=400, detail=f"Điểm tiêu chí {code} không hợp lệ.")
    for code, percentage in payload.management_metrics.items():
        if code not in {
            "unit_result_percent",
            "implementation_percent",
            "cohesion_percent",
        } or not 0 <= percentage <= 100:
            raise HTTPException(status_code=400, detail=f"Tỷ lệ {code} không hợp lệ.")
    row = (
        database_session.query(KPIAssessmentInput)
        .filter(
            KPIAssessmentInput.user_id == user_id,
            KPIAssessmentInput.period_month == period_month,
        )
        .first()
    )
    if row is None:
        row = KPIAssessmentInput(user_id=user_id, period_month=period_month)
        database_session.add(row)
    row.common_scores_json = payload.common_scores
    row.management_metrics_json = payload.management_metrics
    row.reviewed_by = current_user.id
    database_session.commit()
    return get_assessment_inputs(user_id, period_month, database_session, current_user)


@router.get("/ranking")
def ranking(
    month: str | None = None,
    department_id: int | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Return KPI ranking within the viewer's authorized organization scope."""

    period_month = resolve_period_month(month)
    if not is_admin(current_user) and current_user.organization_role not in {
        LEADERSHIP_ROLE,
        UNIT_HEAD_ROLE,
        UNIT_DEPUTY_ROLE,
    }:
        raise HTTPException(status_code=403, detail="Không có quyền xem xếp hạng KPI.")
    if not is_admin(current_user):
        department_id = current_user.department_id
    return _ranking_query(
        database_session,
        period_month,
        department_id,
        descending=True,
        limit=100,
    )


def _ranking_query(
    database_session: Session,
    month: str,
    department_id: int | None,
    descending: bool,
    limit: int,
) -> list[dict]:
    """Query ranked KPI scores for an optional organization unit."""

    query = (
        database_session.query(User, KPIScore)
        .join(KPIScore, KPIScore.user_id == User.id)
        .filter(KPIScore.period_month == month)
        .filter(User.is_kpi_eligible.is_(True))
    )
    if department_id is not None:
        query = query.filter(User.department_id == department_id)
    order_column = (
        KPIScore.total_score.desc() if descending else KPIScore.total_score.asc()
    )
    return [
        {
            "user_id": user.id,
            "full_name": user.full_name,
            "department": user.department.name if user.department else None,
            "score": score.total_score,
            "classification": score.classification,
            "risk_level": score.risk_level,
        }
        for user, score in query.order_by(order_column).limit(limit).all()
    ]


def _kpi_trend(database_session: Session, current_user: User) -> list[dict]:
    """Aggregate monthly KPI averages for the dashboard trend chart."""

    query = database_session.query(
        KPIScore.period_month,
        func.avg(KPIScore.total_score),
    )
    query = apply_score_scope(query, current_user)
    rows = (
        query.group_by(KPIScore.period_month)
        .order_by(KPIScore.period_month.desc())
        .limit(12)
        .all()
    )
    return [
        {"month": period_month, "score": round(float(average_score), 1)}
        for period_month, average_score in reversed(rows)
    ]


def _score_dict(score: KPIScore) -> dict:
    """Serialize a KPI score row."""

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
