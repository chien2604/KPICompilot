"""Centralize access and task-assignment rules for the commune organization."""

from core.organization import (
    ADMIN_ROLE,
    LEADERSHIP_ROLE,
    SPECIALIST_ROLE,
    UNIT_DEPUTY_ROLE,
    UNIT_HEAD_ROLE,
)
from db.models.users import User


def is_admin(user: User) -> bool:
    """Return whether the account has system-wide administrator access."""

    return user.role.lower() == ADMIN_ROLE


def get_user_level(user: User) -> int:
    """Return the persisted hierarchy level, with zero reserved for administrators."""

    return 0 if is_admin(user) else user.permission_level


def can_view_user(viewer: User, target: User) -> bool:
    """Apply organization-wide, unit, and personal personnel visibility."""

    if is_admin(viewer) or viewer.id == target.id:
        return True
    if viewer.organization_role == LEADERSHIP_ROLE:
        return True
    if viewer.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}:
        return viewer.department_id == target.department_id
    return False


def can_assign_to(assigner: User, target: User) -> bool:
    """Enforce the confirmed two-level assignment hierarchy."""

    if assigner.id == target.id:
        return False
    if is_admin(assigner):
        return True
    if assigner.organization_role == LEADERSHIP_ROLE:
        return target.organization_role == UNIT_HEAD_ROLE
    if assigner.department_id is None or assigner.department_id != target.department_id:
        return False
    if assigner.organization_role == UNIT_HEAD_ROLE:
        return target.organization_role in {UNIT_DEPUTY_ROLE, SPECIALIST_ROLE}
    if assigner.organization_role == UNIT_DEPUTY_ROLE:
        return target.organization_role == SPECIALIST_ROLE
    return False


def can_score(scorer: User, target: User) -> bool:
    """Use the same reporting hierarchy for reviewer scoring permission."""

    return is_admin(scorer) or can_assign_to(scorer, target)


def get_assignable_users(assigner: User, all_users: list[User]) -> list[User]:
    """Return active users to whom the current account may assign work."""

    return [user for user in all_users if can_assign_to(assigner, user)]


def can_manage_task(user: User, task_creator_id: int | None) -> bool:
    """Allow administrators and the original assigner to edit or delete a task."""

    return is_admin(user) or user.id == task_creator_id
