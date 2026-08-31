import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from db.database import SessionLocal  # noqa: E402
from core.config import get_settings  # noqa: E402
from services.kpi_template_service import KPITemplateService  # noqa: E402
from services.personnel_import_service import KPICatalogWorkbookReader  # noqa: E402


def main() -> None:
    """Synchronize configured position templates and document type rules."""

    database_session = SessionLocal()
    try:
        settings = get_settings()
        criteria, _catalog = KPICatalogWorkbookReader().read(
            settings.work_catalog_import_path
        )
        KPITemplateService(database_session).replace_templates(criteria)
        database_session.commit()
        print(
            "Đã đồng bộ template và tiêu chí chung theo Quyết định 283/QĐ-UBND."
        )
    except Exception:
        database_session.rollback()
        raise
    finally:
        database_session.close()


if __name__ == "__main__":
    main()
