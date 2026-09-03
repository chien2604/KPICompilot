import re

from core.deps import get_current_user, require_admin
from core.organization import (
    ADMIN_ROLE,
    ADMIN_TEMPLATE,
    LEADERSHIP_ROLE,
    USER_ROLE,
    get_template_or_error,
    list_position_templates,
)
from core.permissions import can_view_user, get_user_level, get_visible_users, is_admin
from core.security import hash_password
from db.database import get_db
from db.models.chat import ChatLog, Conversation
from db.models.departments import Department
from db.models.evidences import TaskEvidence
from db.models.kpi import KPIScore
from db.models.reports import Report
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from fastapi import APIRouter, Depends, HTTPException
from schemas.users import PasswordResetRequest, UserAccountUpdate, UserCreate
from sqlalchemy import delete as sql_delete
from sqlalchemy import update
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["users"])


def normalize_phone_number(phone_number: str) -> str:
    """Normalize a phone number to digits and validate its length."""

    normalized_phone_number = re.sub(r"\D", "", phone_number)
    if len(normalized_phone_number) != 10:
        raise HTTPException(
            status_code=400, detail="Số điện thoại phải có đúng 10 chữ số."
        )
    return normalized_phone_number


def user_to_dict(user: User) -> dict:
    """Serialize a user and personnel profile for API responses."""

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "kpi_role_template": user.kpi_role_template,
        "permission_level": get_user_level(user),
        "organization_role": user.organization_role,
        "organization_domain": user.organization_domain,
        "manager_id": user.manager_id,
        "management_scope": user.management_scope_json,
        "primary_position_code": user.primary_position_code,
        "personnel_type": user.personnel_type,
        "is_kpi_eligible": user.is_kpi_eligible,
        "department_id": user.department_id,
        "department_name": user.department.name if user.department else None,
        "position_title": user.position_title,
        "phone_number": user.phone_number,
        "birth_year": user.birth_year,
        "date_of_birth": user.date_of_birth,
        "ethnicity": user.ethnicity,
        "party_joined_date": user.party_joined_date,
        "general_education": user.general_education,
        "professional_qualification": user.professional_qualification,
        "political_theory": user.political_theory,
        "source_work_area": user.source_work_area,
        "work_areas": [
            {
                "area_code": area.area_code,
                "area_name": area.area_name,
                "is_primary": area.is_primary,
            }
            for area in user.work_areas
        ],
        "import_notes": user.import_notes,
        "avatar_url": user.avatar_url,
        "is_active": user.is_active,
        "is_admin": is_admin(user),
        "account_configured": bool(user.email and user.hashed_password),
    }


def get_user_or_404(database_session: Session, user_id: int) -> User:
    """Return a user or raise a consistent not-found response."""

    user = database_session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")
    return user


def ensure_department_exists(
    database_session: Session,
    department_id: int | None,
) -> None:
    """Reject unknown department identifiers before writing a user profile."""

    if (
        department_id is not None
        and database_session.get(Department, department_id) is None
    ):
        raise HTTPException(status_code=400, detail="Đơn vị không tồn tại trong hệ thống.")


def ensure_unique_account_fields(
    database_session: Session,
    user_id: int | None,
    email: str | None,
    phone_number: str | None,
) -> None:
    """Reject duplicate email or phone values before account changes are committed."""

    if email:
        email_query = database_session.query(User).filter(User.email == email)
        if user_id is not None:
            email_query = email_query.filter(User.id != user_id)
        if email_query.first():
            raise HTTPException(
                status_code=400, detail="Email đã tồn tại trong hệ thống."
            )
    if phone_number:
        phone_query = database_session.query(User).filter(
            User.phone_number == phone_number
        )
        if user_id is not None:
            phone_query = phone_query.filter(User.id != user_id)
        if phone_query.first():
            raise HTTPException(
                status_code=400, detail="Số điện thoại đã tồn tại trong hệ thống."
            )


@router.get("")
def list_users(
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List personnel within organization, unit, or personal visibility."""

    users = database_session.query(User).order_by(User.full_name).all()
    return [user_to_dict(user) for user in get_visible_users(current_user, users)]


@router.get("/position-templates")
def position_templates(_current_user: User = Depends(get_current_user)) -> list[dict]:
    """List configured position templates for account administration."""

    return list_position_templates()


@router.get("/by-department/{department_id}")
def list_by_department(
    department_id: int,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List personnel in an allowed organization unit."""

    can_view_all_units = is_admin(current_user) or (
        current_user.organization_role == LEADERSHIP_ROLE
    )
    if not can_view_all_units and department_id != current_user.department_id:
        raise HTTPException(
            status_code=403, detail="Không có quyền xem nhân sự đơn vị khác."
        )
    users = (
        database_session.query(User)
        .filter(User.department_id == department_id)
        .order_by(User.full_name)
        .all()
    )
    return [
        user_to_dict(user)
        for user in get_visible_users(current_user, users)
    ]


@router.get("/{user_id}")
def get_user(
    user_id: int,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return a personnel profile within the viewer's permitted scope."""

    user = get_user_or_404(database_session, user_id)
    if not can_view_user(current_user, user):
        raise HTTPException(
            status_code=403, detail="Không có quyền xem hồ sơ người này."
        )
    return user_to_dict(user)


@router.post("", status_code=201)
def create_user(
    payload: UserCreate,
    database_session: Session = Depends(get_db),
    _administrator: User = Depends(require_admin),
) -> dict:
    """Create a fully configured user account and personnel profile."""

    normalized_phone_number = (
        normalize_phone_number(payload.phone_number) if payload.phone_number else None
    )
    ensure_department_exists(database_session, payload.department_id)
    ensure_unique_account_fields(
        database_session, None, str(payload.email), normalized_phone_number
    )
    try:
        position_template = get_template_or_error(payload.kpi_role_template)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    user = User(
        **payload.model_dump(
            exclude={
                "password",
                "phone_number",
                "kpi_role_template",
                "organization_role",
                "role",
                "is_active",
            }
        ),
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        phone_number=normalized_phone_number,
        role=USER_ROLE,
        kpi_role_template=position_template.code,
        permission_level=position_template.permission_level,
        organization_role=position_template.organization_role,
        is_active=payload.is_active,
    )
    database_session.add(user)
    database_session.commit()
    database_session.refresh(user)
    return user_to_dict(user)


@router.patch("/{user_id}")
@router.patch("/{user_id}/role", include_in_schema=False)
def update_user(
    user_id: int,
    payload: UserAccountUpdate,
    database_session: Session = Depends(get_db),
    administrator: User = Depends(require_admin),
) -> dict:
    """Update account credentials, profile information, role template, and activation state."""

    user = get_user_or_404(database_session, user_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "department_id" in update_data:
        ensure_department_exists(database_session, payload.department_id)
    requested_role = update_data.get("role")
    if (
        user.id == administrator.id
        and requested_role
        and requested_role.lower() != ADMIN_ROLE
    ):
        raise HTTPException(
            status_code=400, detail="Không thể tự hạ quyền admin của chính mình."
        )

    email = str(payload.email) if payload.email is not None else user.email
    phone_number = (
        normalize_phone_number(payload.phone_number)
        if payload.phone_number is not None
        else user.phone_number
    )
    ensure_unique_account_fields(database_session, user.id, email, phone_number)

    if payload.email is not None:
        user.email = email
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    if payload.phone_number is not None:
        user.phone_number = phone_number

    if payload.role is not None:
        user.role = payload.role.lower()
        if user.role == ADMIN_ROLE:
            user.kpi_role_template = ADMIN_TEMPLATE
            user.permission_level = 0
            user.organization_role = "SYSTEM_ADMIN"
            user.organization_domain = "SYSTEM"
            user.is_kpi_eligible = False
            user.manager_id = None
            user.management_scope_json = {}
    if payload.kpi_role_template is not None and user.role != ADMIN_ROLE:
        try:
            position_template = get_template_or_error(payload.kpi_role_template)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        user.kpi_role_template = position_template.code
        user.permission_level = position_template.permission_level
        user.organization_role = position_template.organization_role

    profile_fields = (
        "position_title",
        "department_id",
        "birth_year",
        "ethnicity",
        "party_joined_date",
        "general_education",
        "professional_qualification",
        "political_theory",
        "date_of_birth",
        "primary_position_code",
        "personnel_type",
        "is_kpi_eligible",
        "source_work_area",
        "import_notes",
        "organization_domain",
        "manager_id",
        "management_scope_json",
    )
    for field_name in profile_fields:
        if field_name in update_data:
            setattr(user, field_name, update_data[field_name])

    if payload.is_active is not None:
        if payload.is_active and (not user.email or not user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="Cần cấu hình email và mật khẩu trước khi kích hoạt tài khoản.",
            )
        user.is_active = payload.is_active

    database_session.commit()
    database_session.refresh(user)
    return user_to_dict(user)


@router.patch("/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    payload: PasswordResetRequest,
    database_session: Session = Depends(get_db),
    _administrator: User = Depends(require_admin),
) -> dict:
    """Set a new password for an existing account."""

    user = get_user_or_404(database_session, user_id)
    user.hashed_password = hash_password(payload.new_password)
    database_session.commit()
    return {
        "status": "success",
        "message": f"Đã đặt lại mật khẩu cho {user.full_name}.",
    }


@router.delete("/{user_id}")
def deactivate_user(
    user_id: int,
    database_session: Session = Depends(get_db),
    administrator: User = Depends(require_admin),
) -> dict:
    """Deactivate an account without deleting its personnel profile."""

    user = get_user_or_404(database_session, user_id)
    if user.id == administrator.id:
        raise HTTPException(
            status_code=400, detail="Không thể vô hiệu hóa tài khoản của chính mình."
        )
    user.is_active = False
    database_session.commit()
    return {
        "status": "success",
        "message": f"Đã vô hiệu hóa tài khoản {user.full_name}.",
    }


@router.delete("/{user_id}/hard")
def delete_user_hard(
    user_id: int,
    database_session: Session = Depends(get_db),
    administrator: User = Depends(require_admin),
) -> dict:
    """Permanently delete a user after removing or detaching related records."""

    user = get_user_or_404(database_session, user_id)
    if user.id == administrator.id:
        raise HTTPException(
            status_code=400, detail="Không thể xóa tài khoản của chính mình."
        )

    try:
        database_session.execute(
            update(Task).where(Task.creator_id == user_id).values(creator_id=None)
        )
        database_session.execute(
            update(Report).where(Report.created_by == user_id).values(created_by=None)
        )
        database_session.execute(
            update(ChatLog).where(ChatLog.user_id == user_id).values(user_id=None)
        )
        database_session.execute(
            update(Conversation)
            .where(Conversation.user_id == user_id)
            .values(user_id=None)
        )
        database_session.execute(
            sql_delete(TaskAssignment).where(TaskAssignment.user_id == user_id)
        )
        database_session.execute(
            sql_delete(KPIScore).where(KPIScore.user_id == user_id)
        )
        database_session.execute(
            sql_delete(TaskEvidence).where(TaskEvidence.uploaded_by == user_id)
        )
        database_session.delete(user)
        database_session.commit()
    except Exception as error:
        database_session.rollback()
        raise HTTPException(
            status_code=500, detail="Không thể xóa người dùng và dữ liệu liên quan."
        ) from error

    return {
        "status": "success",
        "message": f"Đã xóa vĩnh viễn tài khoản {user.full_name}.",
    }
