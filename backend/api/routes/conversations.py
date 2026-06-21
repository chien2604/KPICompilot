from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.conversations import ConversationCreateIn
from services.chatbot_service import ChatbotService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("")
def create_conversation(payload: ConversationCreateIn, db: Session = Depends(get_db)) -> dict:
    return ChatbotService(db).create_conversation(payload.user_id)


@router.get("")
def list_conversations(user_id: int | None = None, db: Session = Depends(get_db)) -> list[dict]:
    return ChatbotService(db).list_conversations(user_id)


@router.get("/{conversation_id}")
def get_conversation(conversation_id: int, user_id: int | None = None, db: Session = Depends(get_db)) -> dict:
    result = ChatbotService(db).get_conversation(conversation_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại")
    return result


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: int, user_id: int | None = None, db: Session = Depends(get_db)) -> dict:
    deleted = ChatbotService(db).delete_conversation(conversation_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại")
    return {"ok": True}
