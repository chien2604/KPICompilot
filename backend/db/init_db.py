from db.database import Base, engine, init_extensions
import db.models  # noqa: F401


def init_db() -> None:
    init_extensions()
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
