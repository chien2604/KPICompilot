import unittest
from types import SimpleNamespace

from core.permissions import (
    can_assign_to,
    can_confirm_kpi,
    can_manage_task,
    can_score,
    can_self_assess,
    can_verify_task_result,
)


def user(
    user_id: int,
    organization_role: str,
    *,
    role: str = "user",
    department_id: int | None = 10,
    manager_id: int | None = None,
    domain: str = "UBND",
    eligible: bool = True,
    scope: dict | None = None,
    areas: tuple[str, ...] = (),
    active: bool = True,
):
    """Build the smallest personnel object required by permission rules."""

    return SimpleNamespace(
        id=user_id,
        role=role,
        organization_role=organization_role,
        organization_domain=domain,
        department_id=department_id,
        manager_id=manager_id,
        is_kpi_eligible=eligible,
        management_scope_json=scope or {},
        work_areas=[SimpleNamespace(area_code=code) for code in areas],
        is_active=active,
    )


class PermissionMatrixTest(unittest.TestCase):
    """Verify the confirmed conservative PoC hierarchy."""

    def test_system_admin_cannot_perform_business_actions(self):
        administrator = user(1, "SYSTEM_ADMIN", role="admin", domain="SYSTEM")
        specialist = user(2, "SPECIALIST", manager_id=3)
        self.assertFalse(can_assign_to(administrator, specialist))
        self.assertFalse(can_score(administrator, specialist))
        self.assertFalse(can_manage_task(administrator, 1))

    def test_ubnd_authority_assigns_only_configured_unit_head(self):
        authority = user(1, "UBND_AUTHORITY", department_id=1, eligible=False)
        head = user(2, "UNIT_HEAD", manager_id=1)
        specialist = user(3, "SPECIALIST", manager_id=2)
        self.assertTrue(can_assign_to(authority, head))
        self.assertFalse(can_assign_to(authority, specialist))

    def test_unit_head_assigns_only_same_unit_staff(self):
        head = user(1, "UNIT_HEAD")
        own_specialist = user(2, "SPECIALIST", manager_id=1)
        other_specialist = user(3, "SPECIALIST", department_id=20, manager_id=4)
        self.assertTrue(can_assign_to(head, own_specialist))
        self.assertFalse(can_assign_to(head, other_specialist))

    def test_inactive_personnel_cannot_receive_new_task(self):
        """Reject a crafted API assignment to an inactive account."""

        head = user(1, "UNIT_HEAD")
        inactive_specialist = user(
            2,
            "SPECIALIST",
            manager_id=1,
            active=False,
        )
        self.assertFalse(can_assign_to(head, inactive_specialist))

    def test_deputy_requires_explicit_overlapping_scope(self):
        deputy = user(
            1,
            "UNIT_DEPUTY",
            scope={"all_department": False, "work_area_codes": ["KTNN"]},
        )
        in_scope = user(2, "SPECIALIST", areas=("KTNN",))
        out_of_scope = user(3, "SPECIALIST", areas=("KTTC",))
        self.assertTrue(can_assign_to(deputy, in_scope))
        self.assertFalse(can_assign_to(deputy, out_of_scope))

    def test_only_direct_manager_can_review(self):
        head = user(1, "UNIT_HEAD")
        specialist = user(2, "SPECIALIST", manager_id=1)
        unrelated_head = user(3, "UNIT_HEAD")
        self.assertTrue(can_score(head, specialist))
        self.assertFalse(can_score(unrelated_head, specialist))

    def test_invalid_manager_role_cannot_review(self):
        """Reject manager links that do not follow the confirmed hierarchy."""

        specialist_manager = user(1, "SPECIALIST")
        specialist = user(2, "SPECIALIST", manager_id=1)
        self.assertFalse(can_score(specialist_manager, specialist))

    def test_inactive_manager_cannot_review(self):
        """Prevent a disabled account from using historical manager links."""

        inactive_head = user(1, "UNIT_HEAD", active=False)
        specialist = user(2, "SPECIALIST", manager_id=1)
        self.assertFalse(can_score(inactive_head, specialist))

    def test_scoped_deputy_can_verify_but_cannot_confirm_kpi(self):
        deputy = user(
            1,
            "UNIT_DEPUTY",
            scope={"all_department": False, "work_area_codes": ["KTNN"]},
        )
        specialist = user(2, "SPECIALIST", manager_id=3, areas=("KTNN",))
        self.assertTrue(can_verify_task_result(deputy, specialist))
        self.assertFalse(can_confirm_kpi(deputy, specialist))

    def test_specialist_can_only_self_assess_own_eligible_profile(self):
        specialist = user(1, "SPECIALIST")
        colleague = user(2, "SPECIALIST")
        self.assertTrue(can_self_assess(specialist, specialist))
        self.assertFalse(can_self_assess(specialist, colleague))


if __name__ == "__main__":
    unittest.main()
