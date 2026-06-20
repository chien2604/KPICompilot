from db.database import Base, engine, init_extensions
import db.models  # noqa: F401


def init_db() -> None:
    init_extensions()
    print("Dropping all existing tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
