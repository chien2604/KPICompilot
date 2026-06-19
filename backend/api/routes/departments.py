from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.departments import Department
from db.models.users import User

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("")
def list_departments(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {"id": item.id, "name": item.name, "code": item.code, "parent_id": item.parent_id}
        for item in db.query(Department).order_by(Department.id).all()
    ]


@router.get("/{department_id}/users")
def department_users(department_id: int, db: Session = Depends(get_db)) -> list[dict]:
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng ban")
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "kpi_role_template": user.kpi_role_template,
            "department_id": user.department_id,
            "department_name": department.name,
            "position_title": user.position_title,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
        }
        for user in db.query(User).filter(User.department_id == department_id).all()
    ]
