"""Auth routes: đăng nhập, lấy thông tin user hiện tại, danh sách user được phép giao việc."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.deps import get_current_user
from core.permissions import can_assign_to, get_assignable_users, get_user_level
from core.security import create_access_token, verify_password
from db.database import get_db
from db.models.users import User
from schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_to_token_response(user: User, token: str) -> TokenResponse:
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        kpi_role_template=user.kpi_role_template,
        position_title=user.position_title,
        department_id=user.department_id,
        department_name=user.department.name if user.department else None,
        avatar_url=user.avatar_url,
        level=get_user_level(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Đăng nhập bằng email + mật khẩu, trả về JWT token."""
    user = db.query(User).filter(User.email == payload.email, User.is_active.is_(True)).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng.")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng.")
    token = create_access_token({"sub": str(user.id)})
    return _user_to_token_response(user, token)


@router.get("/me", response_model=TokenResponse)
def me(current_user: User = Depends(get_current_user)) -> TokenResponse:
    """Trả về thông tin user đang đăng nhập (dùng token hiện tại)."""
    # Tạo lại token mới để gia hạn phiên
    token = create_access_token({"sub": str(current_user.id)})
    return _user_to_token_response(current_user, token)


@router.get("/assignable-users")
def assignable_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Trả về danh sách user mà người dùng hiện tại có quyền giao việc."""
    all_users = db.query(User).filter(User.is_active.is_(True)).all()
    allowed = get_assignable_users(current_user, all_users)
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "position_title": u.position_title,
            "department_id": u.department_id,
            "department_name": u.department.name if u.department else None,
            "role": u.role,
            "kpi_role_template": u.kpi_role_template,
            "avatar_url": u.avatar_url,
            "level": get_user_level(u),
        }
        for u in allowed
    ]
