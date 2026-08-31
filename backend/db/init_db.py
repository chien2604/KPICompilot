import db.models  # noqa: F401
from db.database import Base, engine, init_extensions


def init_db() -> None:
    """Create missing database extensions and tables without deleting existing data."""

    init_extensions()
    Base.metadata.create_all(bind=engine)
    print("Đã khởi tạo extension và các bảng còn thiếu.")


if __name__ == "__main__":
    init_db()
