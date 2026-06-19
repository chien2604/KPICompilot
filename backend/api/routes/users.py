from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.departments import Department
from db.models.users import User

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
    }


@router.get("")
def list_users(db: Session = Depends(get_db)) -> list[dict]:
    return [user_to_dict(user) for user in db.query(User).order_by(User.id).all()]


@router.get("/by-department/{department_id}")
def list_by_department(department_id: int, db: Session = Depends(get_db)) -> list[dict]:
    return [user_to_dict(user) for user in db.query(User).filter(User.department_id == department_id).all()]


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ")
    return user_to_dict(user)
