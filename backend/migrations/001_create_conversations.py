import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND))

from db.database import Base, engine  # noqa: E402
from db.models.chat import (  # noqa: F401,E402
    Conversation,
    ConversationMessage,
    ConversationSummary,
)


def upgrade() -> None:
    """Apply the operation."""

    Base.metadata.create_all(
        bind=engine,
        tables=[
            Conversation.__table__,
            ConversationMessage.__table__,
            ConversationSummary.__table__,
        ],
    )


if __name__ == "__main__":
    upgrade()
