from pathlib import Path
import sys

from sqlalchemy import text

BACKEND = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND))

from db.database import engine  # noqa: E402


def upgrade() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE reports
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE reports
                SET updated_at = COALESCE(updated_at, created_at)
                WHERE updated_at IS NULL
                """
            )
        )


if __name__ == "__main__":
    upgrade()
