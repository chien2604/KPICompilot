from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.users import User
from core.deps import get_current_user, require_admin
from core.permissions import get_user_level, is_admin
from core.security import hash_password
from schemas.users import UserRoleUpdate, UserCreate

router = APIRouter(prefix="/users", tags=["users"])


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "kpi_role_template": user.kpi_role_template,
        "department_id": user.department_id,
        "department_name": user.department.name if user.department else None,
        "position_title": user.position_title,
        "avatar_url": user.avatar_url,
        "is_active": user.is_active,
        "level": get_user_level(user),
        "is_admin": is_admin(user),
    }


@router.get("")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    level = get_user_level(current_user)
    query = db.query(User)
    # Admin xem tất cả; cấp phòng chỉ xem phòng mình
    if not is_admin(current_user) and level >= 3:
        query = query.filter(User.department_id == current_user.department_id)
    return [user_to_dict(user) for user in query.order_by(User.id).all()]


@router.get("/by-department/{department_id}")
def list_by_department(department_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    level = get_user_level(current_user)
    if not is_admin(current_user) and level >= 3 and department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Không có quyền xem nhân sự phòng khác")
    return [user_to_dict(user) for user in db.query(User).filter(User.department_id == department_id).all()]


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ")

    level = get_user_level(current_user)
    if not is_admin(current_user) and level >= 3 and user.department_id != current_user.department_id and user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền xem hồ sơ người này")

    return user_to_dict(user)


# ─── Admin-only endpoints ────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Admin tạo tài khoản người dùng mới."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email đã tồn tại trong hệ thống.")

    new_user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        kpi_role_template=payload.kpi_role_template,
        position_title=payload.position_title,
        department_id=payload.department_id,
        avatar_url=payload.avatar_url,
        is_active=payload.is_active,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return user_to_dict(new_user)


@router.patch("/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    """Admin cập nhật thông tin phân quyền của một user."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    # Không cho admin tự hạ quyền chính mình
    if user.id == admin.id and payload.role and payload.role != "admin":
        raise HTTPException(status_code=400, detail="Không thể tự hạ quyền admin của chính mình.")

    if payload.role is not None:
        user.role = payload.role
    if payload.kpi_role_template is not None:
        user.kpi_role_template = payload.kpi_role_template
    if payload.position_title is not None:
        user.position_title = payload.position_title
    if payload.department_id is not None:
        user.department_id = payload.department_id
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user_to_dict(user)


@router.patch("/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Admin đặt lại mật khẩu cho user."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    new_password = payload.get("new_password", "")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải từ 6 ký tự trở lên.")

    user.hashed_password = hash_password(new_password)
    db.commit()
    return {"status": "success", "message": f"Đã đặt lại mật khẩu cho {user.full_name}."}


@router.delete("/{user_id}")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    """Admin vô hiệu hoá tài khoản (soft delete)."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Không thể vô hiệu hoá tài khoản của chính mình.")

    user.is_active = False
    db.commit()
    return {"status": "success", "message": f"Đã vô hiệu hoá tài khoản {user.full_name}."}


@router.delete("/{user_id}/hard")
def delete_user_hard(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    """Admin xoá vĩnh viễn tài khoản và dữ liệu liên quan."""
    from sqlalchemy import update, delete as sql_delete
    from db.models.tasks import Task, TaskAssignment
    from db.models.reports import Report
    from db.models.kpi import KPIScore
    from db.models.evidences import TaskEvidence
    from db.models.chat import Conversation, ChatLog

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Không thể xoá tài khoản của chính mình.")

    try:
        # Nullify foreign keys that can be null
        db.execute(update(Task).where(Task.creator_id == user_id).values(creator_id=None))
        db.execute(update(Report).where(Report.created_by == user_id).values(created_by=None))
        db.execute(update(ChatLog).where(ChatLog.user_id == user_id).values(user_id=None))
        db.execute(update(Conversation).where(Conversation.user_id == user_id).values(user_id=None))
        
        # Delete related data that cannot be null or makes no sense without user
        db.execute(sql_delete(TaskAssignment).where(TaskAssignment.user_id == user_id))
        db.execute(sql_delete(KPIScore).where(KPIScore.user_id == user_id))
        db.execute(sql_delete(TaskEvidence).where(TaskEvidence.uploaded_by == user_id))

        # Delete user
        db.delete(user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xoá người dùng: {str(e)}")

    return {"status": "success", "message": f"Đã xoá vĩnh viễn tài khoản {user.full_name}."}
