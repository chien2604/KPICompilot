import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.config import get_settings  # noqa: E402
from core.organization import ADMIN_ROLE, ADMIN_TEMPLATE  # noqa: E402
from core.security import hash_password  # noqa: E402
from db.database import SessionLocal  # noqa: E402
from db.models.users import User  # noqa: E402


def create_admin() -> None:
    """Create or update the bootstrap administrator from environment settings."""

    settings = get_settings()
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        raise ValueError(
            "Hãy cấu hình BOOTSTRAP_ADMIN_EMAIL và BOOTSTRAP_ADMIN_PASSWORD trong backend/.env."
        )
    if len(settings.bootstrap_admin_password) < 6:
        raise ValueError("BOOTSTRAP_ADMIN_PASSWORD phải có ít nhất 8 ký tự.")

    database_session = SessionLocal()
    try:
        administrator = (
            database_session.query(User)
            .filter(User.email == settings.bootstrap_admin_email)
            .first()
        )
        if administrator is None:
            administrator = User(
                full_name=settings.bootstrap_admin_name or "Quản trị viên hệ thống",
                email=settings.bootstrap_admin_email,
                phone_number=None,
                role=ADMIN_ROLE,
                kpi_role_template=ADMIN_TEMPLATE,
                permission_level=0,
                organization_role="ADMIN",
                primary_position_code="ADMIN",
                personnel_type="ADMIN",
                is_kpi_eligible=False,
                position_title="Quản trị viên hệ thống",
                ethnicity="Chưa cập nhật",
                party_joined_date="Không ĐV",
                general_education="Chưa cập nhật",
                professional_qualification="Chưa cập nhật",
                political_theory="Chưa cập nhật",
                is_active=True,
            )
            database_session.add(administrator)

        administrator.full_name = (
            settings.bootstrap_admin_name or administrator.full_name
        )
        administrator.hashed_password = hash_password(settings.bootstrap_admin_password)
        administrator.role = ADMIN_ROLE
        administrator.kpi_role_template = ADMIN_TEMPLATE
        administrator.permission_level = 0
        administrator.organization_role = "ADMIN"
        administrator.primary_position_code = "ADMIN"
        administrator.personnel_type = "ADMIN"
        administrator.is_kpi_eligible = False
        administrator.is_active = True
        database_session.commit()
        database_session.refresh(administrator)
        print(
            f"Đã cấu hình tài khoản admin: {administrator.email} (ID {administrator.id})."
        )
    finally:
        database_session.close()


if __name__ == "__main__":
    create_admin()
