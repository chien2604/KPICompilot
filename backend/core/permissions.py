"""Centralize access and task-assignment rules for the commune organization."""

from db.models.users import User

from core.organization import (
    ADMIN_ROLE,
    SPECIALIST_ROLE,
    UBND_AUTHORITY_ROLE,
    UNIT_DEPUTY_ROLE,
    UNIT_HEAD_ROLE,
)


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
    if viewer.organization_role == UBND_AUTHORITY_ROLE:
        return True
    if viewer.organization_role == UNIT_HEAD_ROLE:
        return viewer.department_id == target.department_id
    if viewer.organization_role == UNIT_DEPUTY_ROLE:
        return can_assign_to(viewer, target)
    return False


def can_assign_to(assigner: User, target: User) -> bool:
    """Enforce authority-to-head and same-unit operational assignment."""

    if assigner.id == target.id:
        return False
    if (
        is_admin(assigner)
        or not assigner.is_active
        or assigner.organization_domain != "UBND"
    ):
        return False
    if (
        target.organization_domain != "UBND"
        or not target.is_kpi_eligible
        or not target.is_active
    ):
        return False
    if assigner.organization_role == UBND_AUTHORITY_ROLE:
        return (
            target.organization_role == UNIT_HEAD_ROLE
            and target.manager_id == assigner.id
        )
    if assigner.department_id is None or assigner.department_id != target.department_id:
        return False
    if assigner.organization_role == UNIT_HEAD_ROLE:
        return (
            target.manager_id == assigner.id
            and target.organization_role in {UNIT_DEPUTY_ROLE, SPECIALIST_ROLE}
        )
    if assigner.organization_role == UNIT_DEPUTY_ROLE:
        scope = assigner.management_scope_json or {}
        if not scope.get("all_department"):
            allowed_areas = set(scope.get("work_area_codes", []))
            target_areas = {area.area_code for area in target.work_areas}
            if not allowed_areas or not allowed_areas.intersection(target_areas):
                return False
        return target.organization_role == SPECIALIST_ROLE
    return False


def can_score(scorer: User, target: User) -> bool:
    """Keep a compatibility alias for common-criteria review permission."""

    return can_review_common_criteria(scorer, target)


def can_assign_task(assigner: User, target: User) -> bool:
    """Return whether an account can create an official task for a target."""

    return can_assign_to(assigner, target)


def can_review_task_result(reviewer: User, target: User) -> bool:
    """Allow a direct manager or a scoped deputy to review submitted output."""

    return can_assign_to(reviewer, target)


def can_verify_task_result(reviewer: User, target: User) -> bool:
    """Return human verification authority independently from KPI confirmation."""

    return can_review_task_result(reviewer, target)


def can_self_assess(actor: User, target: User) -> bool:
    """Allow eligible personnel to self-assess without deriving rights from admin."""

    return (
        not is_admin(actor)
        and actor.id == target.id
        and actor.is_active
        and target.organization_domain == "UBND"
        and target.is_kpi_eligible
    )


def can_review_common_criteria(reviewer: User, target: User) -> bool:
    """Allow only the target's configured direct manager to review common criteria."""

    return target.manager_id == reviewer.id and can_assign_to(reviewer, target)


def can_confirm_kpi(reviewer: User, target: User) -> bool:
    """Keep KPI confirmation separate from task assignment and product review."""

    return can_review_common_criteria(reviewer, target)


def get_assignable_users(assigner: User, all_users: list[User]) -> list[User]:
    """Return active users to whom the current account may assign work."""

    return [
        user
        for user in all_users
        if user.is_active and can_assign_task(assigner, user)
    ]


def get_visible_users(viewer: User, all_users: list[User]) -> list[User]:
    """Return personnel visible through organization, unit, or delegated scope."""

    return [user for user in all_users if can_view_user(viewer, user)]


def can_manage_task(user: User, task_creator_id: int | None) -> bool:
    """Allow only the original business assigner to manage a task."""

    return not is_admin(user) and user.id == task_creator_id
