"""Script: seed default password '123456' cho tất cả users demo."""
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND))

from core.security import hash_password  # noqa: E402
from db.database import SessionLocal  # noqa: E402
from db.models.users import User  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        users = db.query(User).all()
        pwd = hash_password("123456")
        for u in users:
            u.hashed_password = pwd
        db.commit()
        print(f"[OK] Da cap nhat mat khau mac dinh '123456' cho {len(users)} user.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
