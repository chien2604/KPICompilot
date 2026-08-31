"""Provide authentication, session identity, and password management routes."""

from core.deps import get_current_user
from core.permissions import get_assignable_users, get_user_level, is_admin
from core.security import create_access_token, hash_password, verify_password
from db.database import get_db
from db.models.users import User
from fastapi import APIRouter, Depends, HTTPException, status
from schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["auth"])


def user_to_token_response(user: User, token: str) -> TokenResponse:
    """Serialize an authenticated user and a newly issued access token."""

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        kpi_role_template=user.kpi_role_template,
        organization_role=user.organization_role,
        position_title=user.position_title,
        department_id=user.department_id,
        department_name=user.department.name if user.department else None,
        avatar_url=user.avatar_url,
        level=get_user_level(user),
        is_admin=is_admin(user),
    )


def authenticate_user(database_session: Session, email: str, password: str) -> User:
    """Validate credentials for an active, fully configured account."""

    user = (
        database_session.query(User)
        .filter(
            User.email == email,
            User.is_active.is_(True),
        )
        .first()
    )
    if (
        not user
        or not user.hashed_password
        or not verify_password(password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng.",
        )
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, database_session: Session = Depends(get_db)
) -> TokenResponse:
    """Authenticate by email and password and return an access token."""

    user = authenticate_user(database_session, str(payload.email), payload.password)
    token = create_access_token({"sub": str(user.id)})
    return user_to_token_response(user, token)


@router.get("/me", response_model=TokenResponse)
def current_identity(current_user: User = Depends(get_current_user)) -> TokenResponse:
    """Return the current account and refresh its access token."""

    token = create_access_token({"sub": str(current_user.id)})
    return user_to_token_response(current_user, token)


@router.get("/assignable-users")
def assignable_users(
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> list[dict]:
    """Return active users within the current account's assignment authority."""

    personnel = database_session.query(User).filter(User.role == "user").all()
    allowed_users = get_assignable_users(current_user, personnel)
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "position_title": user.position_title,
            "department_id": user.department_id,
            "department_name": user.department.name if user.department else None,
            "role": user.role,
            "kpi_role_template": user.kpi_role_template,
            "organization_role": user.organization_role,
            "is_kpi_eligible": user.is_kpi_eligible,
            "avatar_url": user.avatar_url,
            "level": get_user_level(user),
        }
        for user in allowed_users
    ]


def update_password(user: User, old_password: str, new_password: str) -> None:
    """Validate the existing password and replace it with a secure hash."""

    if not user.hashed_password:
        raise HTTPException(
            status_code=400, detail="Tài khoản chưa được thiết lập mật khẩu."
        )
    if not verify_password(old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Mật khẩu cũ không chính xác.")
    user.hashed_password = hash_password(new_password)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    database_session: Session = Depends(get_db),
) -> dict:
    """Change the password for the authenticated account."""

    update_password(current_user, payload.old_password, payload.new_password)
    database_session.commit()
    return {"status": "success", "message": "Đổi mật khẩu thành công."}


@router.post("/change-password-public")
def change_password_public(
    payload: ResetPasswordRequest,
    database_session: Session = Depends(get_db),
) -> dict:
    """Change a password from the login page using current credentials."""

    user = authenticate_user(database_session, str(payload.email), payload.old_password)
    user.hashed_password = hash_password(payload.new_password)
    database_session.commit()
    return {"status": "success", "message": "Đổi mật khẩu thành công."}
