import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from db.database import engine  # noqa: E402


def upgrade() -> None:
    """Add village personnel and account-provisioning columns to existing databases."""

    statements = (
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS unit_type VARCHAR(30) NOT NULL DEFAULT 'VILLAGE'",
        "ALTER TABLE users ALTER COLUMN email DROP NOT NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS permission_level INTEGER NOT NULL DEFAULT 3",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_year INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ethnicity VARCHAR(100) NOT NULL DEFAULT 'Chưa cập nhật'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS party_joined_date VARCHAR(30) NOT NULL DEFAULT 'Không ĐV'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS general_education VARCHAR(50) NOT NULL DEFAULT 'Chưa cập nhật'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS professional_qualification VARCHAR(100) NOT NULL DEFAULT 'Chưa cập nhật'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS political_theory VARCHAR(100) NOT NULL DEFAULT 'Chưa cập nhật'",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_number ON users (phone_number) WHERE phone_number IS NOT NULL",
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


if __name__ == "__main__":
    upgrade()
