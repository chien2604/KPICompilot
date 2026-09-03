from datetime import datetime

from core.deps import get_current_user
from core.organization import (
    LEADERSHIP_ROLE,
    UNIT_DEPUTY_ROLE,
    UNIT_HEAD_ROLE,
    USER_ROLE,
)
from core.permissions import (
    can_confirm_kpi,
    can_review_common_criteria,
    can_score,
    can_self_assess,
    can_view_user,
    get_visible_users,
    is_admin,
)
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
from schemas.kpi import (
    KPIAssessmentInputUpdate,
    KPIReviewerAssessmentUpdate,
    KPISelfAssessmentUpdate,
)
from services.audit_service import record_audit_event
from services.kpi_engine import KPIEngine
from services.task_service import effective_task_status_expression
from services.work_catalog_service import filter_assignable_catalog
from sqlalchemy import func
from sqlalchemy.orm import Session

router = APIRouter(prefix="/kpi", tags=["kpi"])


def visible_user_ids(database_session: Session, current_user: User) -> list[int]:
    """Resolve personnel IDs through the central organization visibility rules."""

    users = database_session.query(User).all()
    return [user.id for user in get_visible_users(current_user, users)]


def resolve_period_month(month: str | None) -> str:
    """Return a validated monthly or quarterly tracking period."""

    period_month = month or datetime.now().strftime("%Y-%m")
    try:
        if "-Q" in period_month:
            year, quarter = period_month.split("-Q")
            if len(year) != 4 or not year.isdigit() or quarter not in {"1", "2", "3", "4"}:
                raise ValueError
        else:
            datetime.strptime(period_month, "%Y-%m")
    except ValueError as error:
        raise HTTPException(
            status_code=400, detail="Kỳ theo dõi phải có định dạng YYYY-MM hoặc YYYY-Q1."
        ) from error
    return period_month


def apply_task_scope(query, current_user: User):
    """Apply organization, unit, or personal task scope to a query."""

    if is_admin(current_user) or current_user.organization_role == LEADERSHIP_ROLE:
        return query
    allowed_user_ids = visible_user_ids(query.session, current_user)
    return query.join(TaskAssignment, TaskAssignment.task_id == Task.id).filter(
        TaskAssignment.user_id.in_(allowed_user_ids)
    )


def apply_score_scope(query, current_user: User):
    """Apply organization, unit, or personal KPI score scope to a query."""

    if is_admin(current_user) or current_user.organization_role == LEADERSHIP_ROLE:
        return query
    return query.filter(
        KPIScore.user_id.in_(visible_user_ids(query.session, current_user))
    )


@router.get("/dashboard")
def dashboard(
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return KPI and task summary data within the current user's scope."""

    period_month = resolve_period_month(month)
    allowed_user_ids = visible_user_ids(database_session, current_user)
    user_query = database_session.query(User).filter(User.role == USER_ROLE)
    user_query = user_query.filter(User.id.in_(allowed_user_ids))

    status_expression = effective_task_status_expression().label("effective_status")
    task_count_query = apply_task_scope(
        database_session.query(
            status_expression,
            func.count(func.distinct(Task.id)),
        ),
        current_user,
    )
    task_counts = dict(task_count_query.group_by(status_expression).all())

    average_query = apply_score_scope(
        database_session.query(func.avg(KPIScore.total_score)).filter(
            KPIScore.period_month == period_month,
            KPIScore.score_status == "CONFIRMED",
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
        "task_completed": task_counts.get("VERIFIED", 0),
        "task_total": sum(task_counts.values()),
        "task_overdue": task_counts.get("OVERDUE", 0),
        "task_status": task_counts,
        "top_users": _ranking_query(
            database_session,
            period_month,
            ranking_department_id,
            descending=True,
            limit=5,
            user_ids=allowed_user_ids,
        )
        if show_rankings
        else [],
        "low_users": _ranking_query(
            database_session,
            period_month,
            ranking_department_id,
            descending=False,
            limit=5,
            user_ids=allowed_user_ids,
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
    allowed_user_ids = visible_user_ids(database_session, current_user)
    department_query = database_session.query(Department).filter(
        Department.unit_type.in_(("LEADERSHIP", "UNIT"))
    )
    if not is_admin(current_user) and current_user.organization_role != LEADERSHIP_ROLE:
        department_query = department_query.filter(Department.id == current_user.department_id)
    result = []
    for department in department_query.order_by(Department.id).all():
        users = database_session.query(User).filter(
            User.department_id == department.id,
            User.id.in_(allowed_user_ids),
        )
        eligible_ids = [user.id for user in users.filter(User.is_kpi_eligible.is_(True)).all()]
        average_kpi = None
        if eligible_ids:
            average_kpi = (
                database_session.query(func.avg(KPIScore.total_score))
                .filter(
                    KPIScore.period_month == period_month,
                    KPIScore.score_status == "CONFIRMED",
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
            "organization_domain": user.organization_domain,
            "manager_id": user.manager_id,
            "management_scope": user.management_scope_json,
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
                "work_catalog_code": task.catalog_code_snapshot,
                "conversion_factor": task.conversion_factor_snapshot,
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
    if not can_review_common_criteria(current_user, user):
        raise HTTPException(
            status_code=403, detail="Không có quyền chấm KPI người này."
        )
    try:
        score = KPIEngine(database_session).recompute_and_save(user_id, period_month)
        record_audit_event(
            database_session,
            actor_id=current_user.id,
            action="KPI_RECOMPUTED",
            entity_type="KPI_SCORE",
            entity_id=score.id,
            after={
                "total_score": score.total_score,
                "period_month": period_month,
                "score_status": score.score_status,
            },
        )
        database_session.commit()
        return _score_dict(score)
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
    rows = filter_assignable_catalog(
        database_session.query(WorkCatalogItem)
        .filter(WorkCatalogItem.is_active.is_(True))
        .order_by(WorkCatalogItem.code)
        .all(),
        target,
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
        "self_scores": row.self_scores_json if row else {},
        "reviewed_scores": row.reviewed_scores_json if row else {},
        "management_review": row.management_review_json if row else {},
        "reviewed_by": row.reviewed_by if row else None,
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
    """Keep old clients compatible while enforcing the new review workflow."""

    period_month = resolve_period_month(month)
    target = database_session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ.")
    if not can_score(current_user, target):
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
    if payload.management_metrics:
        raise HTTPException(
            status_code=422,
            detail=(
                "Không còn hỗ trợ nhập phần trăm quản lý tự do. "
                "Hãy dùng mức xác nhận tại API /review."
            ),
        )
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
        database_session.flush()
    if row.self_assessed_at is None:
        raise HTTPException(status_code=409, detail="Cán bộ chưa hoàn thành tự đánh giá.")
    before = dict(row.reviewed_scores_json or {})
    row.common_scores_json = payload.common_scores
    row.reviewed_scores_json = payload.common_scores
    row.reviewed_by = current_user.id
    row.reviewed_at = datetime.utcnow()
    record_audit_event(
        database_session,
        actor_id=current_user.id,
        action="ASSESSMENT_REVIEWED",
        entity_type="KPI_ASSESSMENT",
        entity_id=row.id,
        before={"scores": before},
        after={"scores": payload.common_scores},
        reason="Compatibility endpoint",
    )
    database_session.commit()
    return get_assessment_inputs(user_id, period_month, database_session, current_user)


def _assessment_row(
    database_session: Session, user_id: int, period_month: str
) -> KPIAssessmentInput:
    """Load or initialize one monthly assessment input row."""

    row = database_session.query(KPIAssessmentInput).filter(
        KPIAssessmentInput.user_id == user_id,
        KPIAssessmentInput.period_month == period_month,
    ).first()
    if row is None:
        row = KPIAssessmentInput(user_id=user_id, period_month=period_month)
        database_session.add(row)
        database_session.flush()
    return row


def _validate_common_scores(
    database_session: Session, target: User, scores: dict[str, float]
) -> None:
    """Validate common scores against the target's configured KPI template."""

    limits = {
        criterion.criterion_code: criterion.max_score
        for criterion in database_session.query(KPICriterion)
        .join(KPITemplate)
        .filter(KPITemplate.code == target.kpi_role_template)
        .all()
    }
    for code, score in scores.items():
        if code not in limits or not 0 <= score <= limits[code]:
            raise HTTPException(
                status_code=400, detail=f"Điểm tiêu chí {code} không hợp lệ."
            )


@router.put("/users/{user_id}/self-assessment")
def save_self_assessment(
    user_id: int,
    payload: KPISelfAssessmentUpdate,
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Save the employee's monthly self-assessment before reviewer input."""

    target = database_session.get(User, user_id)
    if target is None or not can_self_assess(current_user, target):
        raise HTTPException(status_code=400, detail="Hồ sơ không thuộc phạm vi KPI hiện hành.")
    period_month = resolve_period_month(month)
    _validate_common_scores(database_session, target, payload.common_scores)
    row = _assessment_row(database_session, user_id, period_month)
    before = dict(row.self_scores_json or {})
    row.self_scores_json = payload.common_scores
    row.self_assessed_at = datetime.utcnow()
    record_audit_event(
        database_session,
        actor_id=current_user.id,
        action="SELF_ASSESSMENT_SAVED",
        entity_type="KPI_ASSESSMENT",
        entity_id=row.id,
        before=before,
        after=payload.common_scores,
    )
    database_session.commit()
    return get_assessment_inputs(
        user_id, period_month, database_session, current_user
    )


@router.put("/users/{user_id}/review")
def review_assessment(
    user_id: int,
    payload: KPIReviewerAssessmentUpdate,
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Review self-assessment through the configured direct authority."""

    target = database_session.get(User, user_id)
    if target is None or not can_review_common_criteria(current_user, target):
        raise HTTPException(status_code=403, detail="Không có thẩm quyền duyệt đánh giá này.")
    period_month = resolve_period_month(month)
    _validate_common_scores(database_session, target, payload.common_scores)
    levels = {payload.implementation_level, payload.cohesion_level} - {None}
    if levels - {"FULL", "PARTIAL"}:
        raise HTTPException(status_code=400, detail="Mức quản lý chỉ nhận FULL hoặc PARTIAL.")
    row = _assessment_row(database_session, user_id, period_month)
    if row.self_assessed_at is None:
        raise HTTPException(status_code=409, detail="Cán bộ chưa hoàn thành tự đánh giá.")
    before = {
        "scores": row.reviewed_scores_json,
        "management": row.management_review_json,
    }
    row.reviewed_scores_json = payload.common_scores
    row.common_scores_json = payload.common_scores
    row.management_review_json = {
        "implementation_level": payload.implementation_level,
        "cohesion_level": payload.cohesion_level,
    }
    row.reviewed_by = current_user.id
    row.reviewed_at = datetime.utcnow()
    row.review_note = payload.note
    record_audit_event(
        database_session,
        actor_id=current_user.id,
        action="ASSESSMENT_REVIEWED",
        entity_type="KPI_ASSESSMENT",
        entity_id=row.id,
        before=before,
        after={"scores": payload.common_scores, "management": row.management_review_json},
        reason=payload.note,
    )
    database_session.commit()
    return get_assessment_inputs(
        user_id, period_month, database_session, current_user
    )


@router.post("/users/{user_id}/score/confirm")
def confirm_score(
    user_id: int,
    month: str | None = None,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Confirm a complete deterministic score through the direct reviewer."""

    target = database_session.get(User, user_id)
    if target is None or not can_confirm_kpi(current_user, target):
        raise HTTPException(status_code=403, detail="Không có thẩm quyền xác nhận điểm này.")
    period_month = resolve_period_month(month)
    score = database_session.query(KPIScore).filter(
        KPIScore.user_id == user_id,
        KPIScore.period_month == period_month,
    ).order_by(KPIScore.created_at.desc()).first()
    if score is None or score.breakdown_json.get("is_complete") is not True:
        raise HTTPException(status_code=409, detail="Điểm chưa đầy đủ dữ liệu để xác nhận.")
    score.score_status = "CONFIRMED"
    score.confirmed_by = current_user.id
    score.confirmed_at = datetime.utcnow()
    record_audit_event(
        database_session,
        actor_id=current_user.id,
        action="KPI_SCORE_CONFIRMED",
        entity_type="KPI_SCORE",
        entity_id=score.id,
        after={"total_score": score.total_score, "period_month": period_month},
    )
    database_session.commit()
    return _score_dict(score)


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
    if not is_admin(current_user) and current_user.organization_role != LEADERSHIP_ROLE:
        department_id = current_user.department_id
    return _ranking_query(
        database_session,
        period_month,
        department_id,
        descending=True,
        limit=100,
        user_ids=visible_user_ids(database_session, current_user),
    )


def _ranking_query(
    database_session: Session,
    month: str,
    department_id: int | None,
    descending: bool,
    limit: int,
    user_ids: list[int] | None = None,
) -> list[dict]:
    """Query ranked KPI scores for an optional organization unit."""

    query = (
        database_session.query(User, KPIScore)
        .join(KPIScore, KPIScore.user_id == User.id)
        .filter(
            KPIScore.period_month == month,
            KPIScore.score_status == "CONFIRMED",
        )
        .filter(User.is_kpi_eligible.is_(True))
    )
    if department_id is not None:
        query = query.filter(User.department_id == department_id)
    if user_ids is not None:
        query = query.filter(User.id.in_(user_ids))
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
            "reference_level": score.classification,
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
    query = query.filter(KPIScore.score_status == "CONFIRMED")
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
        "reference_level": score.classification,
        "score_status": score.score_status,
        "confirmed_by": score.confirmed_by,
        "confirmed_at": score.confirmed_at,
        "breakdown_json": score.breakdown_json,
        "ai_explanation": score.ai_explanation,
        "risk_level": score.risk_level,
        "created_at": score.created_at,
    }
