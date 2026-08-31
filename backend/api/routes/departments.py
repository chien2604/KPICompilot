from core.deps import get_current_user
from core.organization import LEADERSHIP_ROLE
from core.permissions import is_admin
from db.database import get_db
from db.models.departments import Department
from db.models.users import User
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("")
def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List organization units within the current user's permitted scope."""

    query = db.query(Department)
    if not is_admin(current_user) and current_user.organization_role != LEADERSHIP_ROLE:
        current_department = db.get(Department, current_user.department_id)
        allowed_department_ids = [current_user.department_id]
        if current_department and current_department.parent_id is not None:
            allowed_department_ids.append(current_department.parent_id)
        query = query.filter(Department.id.in_(allowed_department_ids))
    return [
        {
            "id": item.id,
            "name": item.name,
            "code": item.code,
            "unit_type": item.unit_type,
            "parent_id": item.parent_id,
        }
        for item in query.order_by(Department.id).all()
    ]


@router.get("/{department_id}/users")
def department_users(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List personnel in an allowed organization unit."""

    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn vị.")
    can_view_all_units = is_admin(current_user) or (
        current_user.organization_role == LEADERSHIP_ROLE
    )
    if not can_view_all_units and department_id != current_user.department_id:
        raise HTTPException(
            status_code=403, detail="Không có quyền xem nhân sự đơn vị khác."
        )
    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "kpi_role_template": user.kpi_role_template,
            "permission_level": user.permission_level,
            "organization_role": user.organization_role,
            "department_id": user.department_id,
            "department_name": department.name,
            "position_title": user.position_title,
            "phone_number": user.phone_number,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
        }
        for user in db.query(User).filter(User.department_id == department_id).all()
    ]
