"""Logic phân quyền: xác định ai được giao việc / chấm điểm cho ai.

Phân cấp:
  Giám đốc (level 1)       → giao/chấm: Phó GĐ, Trưởng phòng
  Phó giám đốc (level 2)  → giao/chấm: Trưởng phòng, Phó trưởng phòng
  Trưởng phòng (level 3)  → giao/chấm: Phó phòng, Chuyên viên (trong phòng mình)
  Phó phòng (level 4)     → giao/chấm: Chuyên viên (trong phòng mình)
  Chuyên viên (level 5)   → không giao/chấm ai
"""
from db.models.users import User

# Mapping kpi_role_template → level ưu tiên
_TEMPLATE_LEVEL: dict[str, int] = {
    "BAN_GIAM_DOC": 1,          # dùng position_title để phân biệt GĐ vs Phó GĐ
    "TRUONG_PHO_PHONG": 3,      # dùng position_title để phân biệt Trưởng vs Phó
    "CONG_CHUC_KHONG_CHUC_VU": 5,
}

_POSITION_LEVEL: dict[str, int] = {
    "Giám đốc Sở": 1,
    "Phó Giám đốc Sở": 2,
    "Trưởng phòng": 3,
    "Phó trưởng phòng": 4,
    "Chuyên viên": 5,
}


def get_user_level(user: User) -> int:
    """Trả về cấp bậc của user (1 = cao nhất)."""
    if user.position_title and user.position_title in _POSITION_LEVEL:
        return _POSITION_LEVEL[user.position_title]
    return _TEMPLATE_LEVEL.get(user.kpi_role_template, 5)


def can_assign_to(assigner: User, target: User) -> bool:
    """Kiểm tra assigner có quyền giao việc cho target không."""
    a_lvl = get_user_level(assigner)
    t_lvl = get_user_level(target)

    # Không thể giao cho chính mình
    if assigner.id == target.id:
        return False

    # Giám đốc (1): giao cho Phó GĐ (2) và Trưởng phòng (3)
    if a_lvl == 1:
        return t_lvl in (2, 3)

    # Phó GĐ (2): giao cho Trưởng phòng (3) và Phó trưởng phòng (4)
    if a_lvl == 2:
        return t_lvl in (3, 4)

    # Trưởng phòng (3): giao cho Phó phòng (4) và Chuyên viên (5) trong cùng phòng
    if a_lvl == 3:
        return t_lvl in (4, 5) and assigner.department_id == target.department_id

    # Phó phòng (4): giao cho Chuyên viên (5) trong cùng phòng
    if a_lvl == 4:
        return t_lvl == 5 and assigner.department_id == target.department_id

    return False


def can_score(scorer: User, target: User) -> bool:
    """Kiểm tra scorer có quyền chấm điểm KPI cho target không."""
    # Quyền chấm điểm giống quyền giao việc
    return can_assign_to(scorer, target)


def get_assignable_users(assigner: User, all_users: list[User]) -> list[User]:
    """Trả về danh sách user mà assigner có thể giao việc."""
    return [u for u in all_users if can_assign_to(assigner, u)]
