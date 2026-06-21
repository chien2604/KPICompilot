from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND))

from db.database import Base, engine  # noqa: E402
from db.models.chat import Conversation, ConversationMessage, ConversationSummary  # noqa: F401,E402


def upgrade() -> None:
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
