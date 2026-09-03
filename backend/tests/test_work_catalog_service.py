import unittest
from types import SimpleNamespace

from services.work_catalog_service import is_catalog_item_assignable


def catalog(
    scope: str,
    *,
    code: str = "DC.01",
    department_code: str | None = None,
):
    """Build one catalog record required by the matching rule."""

    return SimpleNamespace(
        is_active=True,
        catalog_scope=scope,
        code=code,
        department_code=department_code,
    )


def target(
    role: str,
    *,
    department_code: str = "PHONG_KINH_TE",
    areas=(),
):
    """Build one eligible personnel profile required by the matching rule."""

    return SimpleNamespace(
        is_kpi_eligible=True,
        organization_role=role,
        department=SimpleNamespace(code=department_code),
        work_areas=[SimpleNamespace(area_code=area) for area in areas],
    )


class WorkCatalogMatchingTest(unittest.TestCase):
    """Protect server-side matching of Decision 283 catalog items."""

    def test_common_item_is_available_to_eligible_personnel(self):
        """Allow the common catalog for every eligible profile."""

        self.assertTrue(
            is_catalog_item_assignable(catalog("COMMON"), target("SPECIALIST"))
        )

    def test_leadership_item_is_not_available_to_specialist(self):
        """Restrict leadership catalog records to unit management roles."""

        self.assertFalse(
            is_catalog_item_assignable(
                catalog("LEADERSHIP"),
                target("SPECIALIST"),
            )
        )

    def test_department_item_requires_department_and_area(self):
        """Match a specialist to both department and normalized work-area prefix."""

        item = catalog(
            "DEPARTMENT",
            code="KTNN.01",
            department_code="PHONG_KINH_TE",
        )
        self.assertTrue(
            is_catalog_item_assignable(
                item,
                target("SPECIALIST", areas=("KTNN",)),
            )
        )
        self.assertFalse(
            is_catalog_item_assignable(
                item,
                target("SPECIALIST", areas=("KTTC",)),
            )
        )

    def test_unit_head_can_use_department_catalog(self):
        """Allow a unit head to assign all approved records of their own unit."""

        item = catalog(
            "DEPARTMENT",
            code="KTNN.01",
            department_code="PHONG_KINH_TE",
        )
        self.assertTrue(is_catalog_item_assignable(item, target("UNIT_HEAD")))


if __name__ == "__main__":
    unittest.main()
