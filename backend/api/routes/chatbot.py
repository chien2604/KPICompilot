from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.deps import get_current_user
from db.database import get_db
from db.models.users import User
from schemas.chatbot import ChatbotMessageIn
from services.chatbot_service import ChatbotService

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.post("/message")
def chatbot_message(
    payload: ChatbotMessageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Gửi tin nhắn tới AI Copilot. Yêu cầu Bearer token hợp lệ."""
    return ChatbotService(db).answer(
        user=current_user,
        message=payload.message,
        month=payload.month,
        department_id=payload.department_id,
        conversation_id=payload.conversation_id,
    )
