from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversationCreateIn(BaseModel):
    """Represent conversation create in data and behavior."""

    user_id: int | None = None


class ConversationOut(BaseModel):
    """Represent conversation out data and behavior."""

    conversation_id: int
    user_id: int | None = None
    title: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


class ConversationMessageOut(BaseModel):
    """Represent conversation message out data and behavior."""

    message_id: int
    conversation_id: int
    role: str
    content: str
    intent: str | None = None
    metadata_json: dict = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailOut(BaseModel):
    """Represent conversation detail out data and behavior."""

    conversation: ConversationOut
    messages: list[ConversationMessageOut]
    summary: str = ""
