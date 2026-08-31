from core.deps import get_current_user
from db.database import get_db
from db.models.users import User
from fastapi import APIRouter, Depends, HTTPException
from schemas.conversations import ConversationCreateIn
from services.chatbot_service import ChatbotService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("")
def create_conversation(
    _payload: ConversationCreateIn,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a conversation owned by the authenticated account."""

    return ChatbotService(database_session).create_conversation(current_user.id)


@router.get("")
def list_conversations(
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List conversations owned by the authenticated account."""

    return ChatbotService(database_session).list_conversations(current_user.id)


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: int,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return an owned conversation and its messages."""

    result = ChatbotService(database_session).get_conversation(
        conversation_id, current_user.id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại")
    return result


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    database_session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Soft-delete an owned conversation."""

    deleted = ChatbotService(database_session).delete_conversation(
        conversation_id, current_user.id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại")
    return {"ok": True}
