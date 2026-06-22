from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.chatbot import ChatbotMessageIn
from services.chatbot_service import ChatbotService

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.post("/message")
def chatbot_message(payload: ChatbotMessageIn, db: Session = Depends(get_db)) -> dict:
    return ChatbotService(db).answer(
        user_id=payload.user_id,
        message=payload.message,
        month=payload.month,
        department_id=payload.department_id,
        conversation_id=payload.conversation_id,
    )
