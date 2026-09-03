from core.organization import UNIT_DEPUTY_ROLE, UNIT_HEAD_ROLE
from db.models.kpi import WorkCatalogItem
from db.models.users import User


def is_catalog_item_assignable(
    catalog_item: WorkCatalogItem,
    target: User,
) -> bool:
    """Return whether an approved catalog item matches one personnel profile."""

    if not catalog_item.is_active or not target.is_kpi_eligible:
        return False
    if catalog_item.catalog_scope == "COMMON":
        return True
    if catalog_item.catalog_scope == "LEADERSHIP":
        return target.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}
    if catalog_item.catalog_scope != "DEPARTMENT" or target.department is None:
        return False
    if catalog_item.department_code != target.department.code:
        return False
    if target.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}:
        return True
    area_codes = {area.area_code for area in target.work_areas}
    return any(
        catalog_item.code.startswith(f"{area_code}.")
        for area_code in area_codes
    )


def filter_assignable_catalog(
    catalog_items: list[WorkCatalogItem],
    target: User,
) -> list[WorkCatalogItem]:
    """Filter active catalog records through the authoritative matching rule."""

    return [
        item
        for item in catalog_items
        if is_catalog_item_assignable(item, target)
    ]
