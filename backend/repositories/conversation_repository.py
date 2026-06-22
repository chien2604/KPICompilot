from datetime import datetime

from sqlalchemy.orm import Session

from db.models.chat import Conversation, ConversationMessage, ConversationSummary


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user_id: int | None, title: str = "Cuộc hội thoại mới") -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_active(self, user_id: int | None = None) -> list[Conversation]:
        query = self.db.query(Conversation).filter(Conversation.is_deleted.is_(False))
        if user_id is not None:
            query = query.filter(Conversation.user_id == user_id)
        return query.order_by(Conversation.updated_at.desc()).all()

    def get_active(self, conversation_id: int, user_id: int | None = None) -> Conversation | None:
        query = self.db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id,
            Conversation.is_deleted.is_(False),
        )
        if user_id is not None:
            query = query.filter(Conversation.user_id == user_id)
        return query.first()

    def update_title(self, conversation: Conversation, title: str) -> Conversation:
        conversation.title = title.strip()[:255] or "Cuộc hội thoại mới"
        conversation.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def soft_delete(self, conversation: Conversation) -> None:
        conversation.is_deleted = True
        conversation.updated_at = datetime.utcnow()
        self.db.commit()

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        intent: str | None = None,
        metadata_json: dict | None = None,
    ) -> ConversationMessage:
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            intent=intent,
            metadata_json=metadata_json or {},
        )
        conversation = self.db.get(Conversation, conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_messages(self, conversation_id: int, limit: int | None = None) -> list[ConversationMessage]:
        query = (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        if limit:
            rows = query.order_by(None).order_by(ConversationMessage.created_at.desc()).limit(limit).all()
            return list(reversed(rows))
        return query.all()

    def count_messages(self, conversation_id: int) -> int:
        return self.db.query(ConversationMessage).filter(ConversationMessage.conversation_id == conversation_id).count()

    def get_summary(self, conversation_id: int) -> ConversationSummary | None:
        return self.db.get(ConversationSummary, conversation_id)

    def upsert_summary(self, conversation_id: int, summary: str) -> ConversationSummary:
        row = self.db.get(ConversationSummary, conversation_id)
        if not row:
            row = ConversationSummary(conversation_id=conversation_id, summary=summary)
            self.db.add(row)
        else:
            row.summary = summary
            row.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(row)
        return row
