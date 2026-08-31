from pydantic import BaseModel


class ChatbotMessageIn(BaseModel):
    """Payload gửi lên từ client. user_id KHÔNG cần truyền — lấy từ JWT token."""

    conversation_id: int | None = None
    message: str
    month: str | None = None
    # department_id chỉ cần khi muốn filter theo phòng cụ thể (override role-based scope)
    department_id: int | None = None


class ChatbotMessageOut(BaseModel):
    """Represent chatbot message out data and behavior."""

    answer: str
    intent: str
    conversation_id: int | None = None
    data: dict = {}
    sources: list = []
