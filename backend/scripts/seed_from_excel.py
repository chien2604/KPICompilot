from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND))

from db.database import SessionLocal  # noqa: E402
from services.excel_rule_loader import ExcelRuleLoader  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        ExcelRuleLoader(db, ROOT).seed()
    finally:
        db.close()


if __name__ == "__main__":
    main()
