"""Add commune personnel, work catalog, and Decree 335 assessment structures."""

import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import db.models  # noqa: E402,F401
from db.database import Base, engine  # noqa: E402
from db.models.kpi import KPIAssessmentInput, WorkCatalogItem  # noqa: E402
from db.models.users import UserWorkArea  # noqa: E402


def upgrade() -> None:
    """Create new tables and add backward-compatible columns to existing tables."""

    statements = (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_role VARCHAR(40) NOT NULL DEFAULT 'SPECIALIST'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS primary_position_code VARCHAR(80) NOT NULL DEFAULT 'CHUA_XAC_DINH'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS personnel_type VARCHAR(30) NOT NULL DEFAULT 'CONG_CHUC'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_kpi_eligible BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth DATE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS source_work_area TEXT NOT NULL DEFAULT 'Chưa cập nhật'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS import_notes TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS work_catalog_item_id INTEGER REFERENCES work_catalog_items(id)",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS quality_percent DOUBLE PRECISION NOT NULL DEFAULT 100",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS major_error_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE task_assignments ADD COLUMN IF NOT EXISTS late_count INTEGER NOT NULL DEFAULT 0",
        "CREATE INDEX IF NOT EXISTS ix_users_organization_role ON users (organization_role)",
        "CREATE INDEX IF NOT EXISTS ix_users_is_kpi_eligible ON users (is_kpi_eligible)",
        "CREATE INDEX IF NOT EXISTS ix_tasks_work_catalog_item_id ON tasks (work_catalog_item_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_kpi_assessment_user_period ON kpi_assessment_inputs (user_id, period_month)",
    )
    with engine.begin() as connection:
        Base.metadata.create_all(
            bind=connection,
            tables=[
                WorkCatalogItem.__table__,
                KPIAssessmentInput.__table__,
                UserWorkArea.__table__,
            ],
        )
        for statement in statements:
            connection.execute(text(statement))


if __name__ == "__main__":
    upgrade()
