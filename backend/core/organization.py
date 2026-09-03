"""Define organization roles and KPI templates for UBND xã Nghĩa Lâm."""

from dataclasses import dataclass

ADMIN_ROLE = "admin"
USER_ROLE = "user"
ADMIN_TEMPLATE = "ADMIN"

SYSTEM_ADMIN_ROLE = "SYSTEM_ADMIN"
UBND_AUTHORITY_ROLE = "UBND_AUTHORITY"
# Kept as an import alias for older modules and persisted data during migration.
LEADERSHIP_ROLE = UBND_AUTHORITY_ROLE
UNIT_HEAD_ROLE = "UNIT_HEAD"
UNIT_DEPUTY_ROLE = "UNIT_DEPUTY"
SPECIALIST_ROLE = "SPECIALIST"
OUT_OF_SCOPE_ROLE = "OUT_OF_SCOPE"


@dataclass(frozen=True)
class PositionTemplate:
    """Describe one organization role, KPI template, and permission level."""

    code: str
    name: str
    permission_level: int
    organization_role: str


POSITION_TEMPLATES = (
    PositionTemplate(
        code="LANH_DAO_XA",
        name="Người có thẩm quyền UBND xã",
        permission_level=1,
        organization_role=UBND_AUTHORITY_ROLE,
    ),
    PositionTemplate(
        code="LANH_DAO_DON_VI",
        name="Trưởng đơn vị",
        permission_level=2,
        organization_role=UNIT_HEAD_ROLE,
    ),
    PositionTemplate(
        code="PHO_LANH_DAO_DON_VI",
        name="Phó trưởng đơn vị",
        permission_level=3,
        organization_role=UNIT_DEPUTY_ROLE,
    ),
    PositionTemplate(
        code="CHUYEN_MON_NGHIEP_VU",
        name="Công chức chuyên môn, nghiệp vụ",
        permission_level=4,
        organization_role=SPECIALIST_ROLE,
    ),
    PositionTemplate(
        code="CHUA_THUOC_PHAM_VI_KPI",
        name="Nhân sự ngoài phạm vi KPI UBND",
        permission_level=5,
        organization_role=OUT_OF_SCOPE_ROLE,
    ),
)

TEMPLATE_BY_CODE = {template.code: template for template in POSITION_TEMPLATES}


def resolve_position_template(
    organization_role: str,
) -> PositionTemplate:
    """Resolve a template from an explicit organization role produced by the importer."""

    for template in POSITION_TEMPLATES:
        if template.organization_role == organization_role:
            return template
    raise ValueError(f"Vai trò tổ chức không hợp lệ: {organization_role}")


def get_template_or_error(template_code: str) -> PositionTemplate:
    """Return a configured position template or raise a validation error."""

    template = TEMPLATE_BY_CODE.get(template_code)
    if template is None:
        raise ValueError(f"Template chức vụ không hợp lệ: {template_code}")
    return template


def list_position_templates() -> list[dict]:
    """Return position templates in an API-friendly structure."""

    return [
        {
            "code": template.code,
            "name": template.name,
            "permission_level": template.permission_level,
            "organization_role": template.organization_role,
        }
        for template in POSITION_TEMPLATES
    ]
