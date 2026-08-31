import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.config import get_settings  # noqa: E402
from db.database import SessionLocal  # noqa: E402
from services.personnel_import_service import PersonnelImportService  # noqa: E402


def main() -> None:
    """Reset PoC data and import approved personnel and KPI workbook sources."""

    database_session = SessionLocal()
    try:
        result = PersonnelImportService(
            database_session, get_settings()
        ).reset_and_import()
        print(
            "Đã nhập "
            f"{result['personnel_count']} cán bộ thuộc {result['department_count']} đơn vị, "
            f"{result['work_catalog_count']} mã công việc vào {result['organization']}."
        )
    except Exception:
        database_session.rollback()
        raise
    finally:
        database_session.close()


if __name__ == "__main__":
    main()
