import json
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_layer.llm_client import get_llm_client
from ai_layer.rag.graph_rag_service import GraphRAGService
from db.models.chat import ChatLog, Conversation
from db.models.departments import Department
from db.models.kpi import KPIScore
from db.models.tasks import Task
from db.models.users import User
from repositories.conversation_repository import ConversationRepository


PROMPT_PATH = Path(__file__).resolve().parents[1] / "ai_layer" / "prompts" / "chatbot_copilot_prompt.txt"


class ChatbotService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm = get_llm_client()
        self.repo = ConversationRepository(db)

    def create_conversation(self, user_id: int | None = None) -> dict:
        return self._conversation_to_dict(self.repo.create(user_id=user_id))

    def list_conversations(self, user_id: int | None = None) -> list[dict]:
        return [self._conversation_to_dict(item) for item in self.repo.list_active(user_id)]

    def get_conversation(self, conversation_id: int, user_id: int | None = None) -> dict | None:
        conversation = self.repo.get_active(conversation_id, user_id)
        if not conversation:
            return None
        summary = self.repo.get_summary(conversation.conversation_id)
        return {
            "conversation": self._conversation_to_dict(conversation),
            "messages": [self._message_to_dict(item) for item in self.repo.list_messages(conversation.conversation_id)],
            "summary": summary.summary if summary else "",
        }

    def delete_conversation(self, conversation_id: int, user_id: int | None = None) -> bool:
        conversation = self.repo.get_active(conversation_id, user_id)
        if not conversation:
            return False
        self.repo.soft_delete(conversation)
        return True

    def answer(
        self,
        user_id: int | None,
        message: str,
        month: str | None,
        department_id: int | None,
        conversation_id: int | None = None,
    ) -> dict:
        conversation = self._get_or_create_conversation(conversation_id, user_id)
        previous_messages = self.repo.list_messages(conversation.conversation_id, limit=12)
        previous_user_messages = [item for item in previous_messages if item.role == "user"]
        summary = self.repo.get_summary(conversation.conversation_id)
        conversation_summary = summary.summary if summary else ""

        intent = self.detect_intent(message)
        data = self._structured_data(intent, month, department_id)
        rag_context = GraphRAGService(self.db).build_chat_context(message, user_id, department_id)
        user_prompt = self._build_user_prompt(
            history=self._format_history(previous_messages),
            conversation_summary=conversation_summary,
            message=message,
            structured_data=data,
            rag_context=rag_context,
        )
        sources = rag_context.get("vectors", [])[:3]

        self.repo.add_message(
            conversation.conversation_id,
            role="user",
            content=message,
            intent=intent,
            metadata_json={"month": month, "department_id": department_id},
        )

        if not previous_user_messages:
            title = self._generate_title(message)
            conversation = self.repo.update_title(conversation, title)

        try:
            answer = self.llm.complete(user_prompt, system_prompt=self._load_system_prompt())
        except Exception:
            answer = self._fallback_answer(intent, data)

        assistant_message = self.repo.add_message(
            conversation.conversation_id,
            role="assistant",
            content=answer,
            intent=intent,
            metadata_json={"structured_data": data, "sources": sources},
        )

        self.db.add(ChatLog(user_id=user_id, question=message, intent=intent, answer=answer, sources_json=sources))
        self.db.commit()

        self._summarize_if_needed(conversation.conversation_id)

        return {
            "answer": answer,
            "intent": intent,
            "data": data,
            "sources": sources,
            "conversation_id": conversation.conversation_id,
            "conversation": self._conversation_to_dict(conversation),
            "message": self._message_to_dict(assistant_message),
        }

    def detect_intent(self, message: str) -> str:
        lower = message.lower()
        if "nguy cơ" in lower or "không đạt" in lower or "rủi ro" in lower:
            return "KPI_RISK_USERS"
        if "phòng" in lower and ("chậm" in lower or "quá hạn" in lower):
            return "SLOW_DEPARTMENTS"
        if "vì sao" in lower or "tại sao" in lower or "điểm thấp" in lower:
            return "EMPLOYEE_PROFILE"
        if "nhiệm vụ" in lower or "tiến độ" in lower:
            return "TASK_STATUS"
        if "minh chứng" in lower:
            return "EVIDENCE_EXPLAIN"
        if "báo cáo" in lower:
            return "GENERATE_REPORT"
        return "GENERAL_HELP"

    def _get_or_create_conversation(self, conversation_id: int | None, user_id: int | None) -> Conversation:
        if conversation_id:
            conversation = self.repo.get_active(conversation_id, user_id)
            if conversation:
                return conversation
        return self.repo.create(user_id=user_id)

    def _load_system_prompt(self) -> str:
        return PROMPT_PATH.read_text(encoding="utf-8")

    def _build_user_prompt(
        self,
        history: str,
        conversation_summary: str,
        message: str,
        structured_data: dict,
        rag_context: dict,
    ) -> str:
        return (
            "LỊCH SỬ HỘI THOẠI\n\n"
            f"{history or '(chưa có lịch sử)'}\n\n"
            "---\n\n"
            "TÓM TẮT HỘI THOẠI\n\n"
            f"{conversation_summary or '(chưa có tóm tắt)'}\n\n"
            "---\n\n"
            "CÂU HỎI HIỆN TẠI\n\n"
            f"{message}\n\n"
            "---\n\n"
            "DỮ LIỆU HỆ THỐNG\n\n"
            f"{json.dumps(structured_data, ensure_ascii=False, indent=2)}\n\n"
            "---\n\n"
            "GRAPH RAG\n\n"
            f"{json.dumps(rag_context, ensure_ascii=False, indent=2)}\n\n"
            "---\n\n"
            "Yêu cầu:\n"
            "- Luôn ưu tiên dữ liệu hệ thống.\n"
            "- Không bịa số liệu.\n"
            "- Không bỏ qua ngữ cảnh hội thoại trước đó.\n"
        )

    def _format_history(self, messages: list) -> str:
        rows = []
        for item in messages:
            label = {"user": "User", "assistant": "Assistant", "system": "System"}.get(item.role, item.role)
            rows.append(f"{label}: {item.content}")
        return "\n\n".join(rows)

    def _generate_title(self, first_message: str) -> str:
        prompt = (
            "Tóm tắt câu hỏi dưới đây thành tiêu đề ngắn.\n\n"
            "Yêu cầu:\n"
            "- tối đa 8 từ\n"
            "- không dấu ngoặc\n"
            "- không giải thích\n"
            "- chỉ trả về tiêu đề\n\n"
            f"Câu hỏi:\n{first_message}"
        )
        try:
            raw = self.llm.complete(prompt).strip()
        except Exception:
            raw = first_message.strip()
        title = raw.replace('"', "").replace("'", "").strip()
        words = title.split()
        return " ".join(words[:8]) or "Hội thoại KPI"

    def _summarize_if_needed(self, conversation_id: int) -> None:
        count = self.repo.count_messages(conversation_id)
        if count < 20 or count % 20 != 0:
            return
        messages = self.repo.list_messages(conversation_id, limit=20)
        current_summary = self.repo.get_summary(conversation_id)
        prompt = (
            "Tóm tắt hội thoại dưới đây để dùng làm memory cho AI Copilot.\n"
            "Yêu cầu: ngắn gọn, tiếng Việt, giữ lại chủ đề chính, cá nhân/phòng ban được nhắc và câu hỏi đang theo đuổi.\n\n"
            f"Tóm tắt hiện tại:\n{current_summary.summary if current_summary else '(chưa có)'}\n\n"
            f"Tin nhắn gần đây:\n{self._format_history(messages)}"
        )
        try:
            summary = self.llm.complete(prompt)
        except Exception:
            summary = self._format_history(messages)[-1800:]
        self.repo.upsert_summary(conversation_id, summary.strip())

    def _structured_data(self, intent: str, month: str | None, department_id: int | None) -> dict:
        period = month or "2026-06"
        if intent == "KPI_RISK_USERS":
            rows = (
                self.db.query(User.full_name, Department.name, KPIScore.total_score, KPIScore.risk_level)
                .join(KPIScore, KPIScore.user_id == User.id)
                .outerjoin(Department, Department.id == User.department_id)
                .filter(KPIScore.period_month == period, KPIScore.risk_level.in_(["HIGH", "MEDIUM"]))
                .order_by(KPIScore.total_score.asc())
                .limit(8)
                .all()
            )
            return {"period": period, "risk_users": [dict(name=r[0], department=r[1], score=r[2], risk=r[3]) for r in rows]}
        if intent == "SLOW_DEPARTMENTS":
            rows = (
                self.db.query(Department.name, func.count(Task.id))
                .join(Task, Task.department_id == Department.id)
                .filter(Task.status == "OVERDUE")
                .group_by(Department.name)
                .order_by(func.count(Task.id).desc())
                .all()
            )
            return {"slow_departments": [{"department": r[0], "overdue_tasks": r[1]} for r in rows]}
        rows = self.db.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
        return {"task_status": {status: count for status, count in rows}}

    def _fallback_answer(self, intent: str, data: dict) -> str:
        if intent == "KPI_RISK_USERS":
            names = [item["name"] for item in data.get("risk_users", [])[:5]]
            return "Nhóm có nguy cơ không đạt KPI gồm: " + (", ".join(names) if names else "chưa có dữ liệu rủi ro.")
        if intent == "SLOW_DEPARTMENTS":
            rows = data.get("slow_departments", [])
            if not rows:
                return "Chưa ghi nhận phòng ban chậm tiến độ trong dữ liệu hiện có."
            return "Phòng chậm tiến độ nổi bật: " + ", ".join(f"{item['department']} ({item['overdue_tasks']} nhiệm vụ quá hạn)" for item in rows[:5])
        return "Đã lấy được dữ liệu nghiệp vụ, nhưng LLM thật chưa phản hồi. Vui lòng kiểm tra cấu hình LLM, quota hoặc kết nối mạng."

    def _conversation_to_dict(self, conversation: Conversation) -> dict:
        return {
            "conversation_id": conversation.conversation_id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "is_deleted": conversation.is_deleted,
        }

    def _message_to_dict(self, message) -> dict:
        return {
            "message_id": message.message_id,
            "conversation_id": message.conversation_id,
            "role": message.role,
            "content": message.content,
            "intent": message.intent,
            "metadata_json": message.metadata_json or {},
            "created_at": message.created_at,
        }
