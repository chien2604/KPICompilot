from pydantic import BaseModel


class ChatbotMessageIn(BaseModel):
    user_id: int | None = None
    conversation_id: int | None = None
    message: str
    month: str | None = None
    department_id: int | None = None


class ChatbotMessageOut(BaseModel):
    answer: str
    intent: str
    conversation_id: int | None = None
    data: dict = {}
    sources: list = []
