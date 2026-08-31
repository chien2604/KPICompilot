from collections.abc import Generator

from core.config import get_settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Represent base data and behavior."""

    pass


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Return the db."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_extensions() -> None:
    """Initialize the extensions."""

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
