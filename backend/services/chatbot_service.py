import json
import logging
from datetime import datetime
from pathlib import Path

from ai_layer.llm_client import get_llm_client
from ai_layer.rag.graph_rag_service import GraphRAGService
from core.organization import (
    LEADERSHIP_ROLE,
    UNIT_DEPUTY_ROLE,
    UNIT_HEAD_ROLE,
)
from core.permissions import is_admin
from db.models.chat import ChatLog, Conversation
from db.models.departments import Department
from db.models.kpi import KPIScore
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from repositories.conversation_repository import ConversationRepository
from sqlalchemy import func
from sqlalchemy.orm import Session

PROMPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "ai_layer"
    / "prompts"
    / "chatbot_copilot_prompt.txt"
)
INTENT_PROMPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "ai_layer"
    / "prompts"
    / "intent_router_prompt.txt"
)
LOGGER = logging.getLogger(__name__)


class ChatbotService:
    """Answer scoped leadership questions and persist conversation memory."""

    def __init__(self, db: Session) -> None:
        """Initialize the chatbot service."""

        self.db = db
        self.llm = get_llm_client()
        self.repo = ConversationRepository(db)

    def create_conversation(self, user_id: int | None = None) -> dict:
        """Create the conversation."""

        return self._conversation_to_dict(self.repo.create(user_id=user_id))

    def list_conversations(self, user_id: int | None = None) -> list[dict]:
        """List the conversations."""

        return [
            self._conversation_to_dict(item) for item in self.repo.list_active(user_id)
        ]

    def get_conversation(
        self, conversation_id: int, user_id: int | None = None
    ) -> dict | None:
        """Return the conversation."""

        conversation = self.repo.get_active(conversation_id, user_id)
        if not conversation:
            return None
        summary = self.repo.get_summary(conversation.conversation_id)
        return {
            "conversation": self._conversation_to_dict(conversation),
            "messages": [
                self._message_to_dict(item)
                for item in self.repo.list_messages(conversation.conversation_id)
            ],
            "summary": summary.summary if summary else "",
        }

    def delete_conversation(
        self, conversation_id: int, user_id: int | None = None
    ) -> bool:
        """Delete the conversation."""

        conversation = self.repo.get_active(conversation_id, user_id)
        if not conversation:
            return False
        self.repo.soft_delete(conversation)
        return True

    def answer(
        self,
        user: User,
        message: str,
        month: str | None,
        department_id: int | None,
        conversation_id: int | None = None,
    ) -> dict:
        """Answer the operation."""

        access_scope = self._access_scope(user)
        has_organization_scope = access_scope == 0
        effective_dept_id = (
            department_id if has_organization_scope else user.department_id
        )

        conversation = self._get_or_create_conversation(conversation_id, user.id)
        previous_messages = self.repo.list_messages(
            conversation.conversation_id, limit=12
        )
        previous_user_messages = [m for m in previous_messages if m.role == "user"]
        conversation_summary = ""
        if len(previous_messages) > 10:
            summary = self.repo.get_summary(conversation.conversation_id)
            conversation_summary = summary.summary if summary else ""

        # Sử dụng LLM Intent Router (có fallback về regex)
        intent = self.detect_intent(message, previous_messages=previous_messages)
        data = self._structured_data(
            intent, month, access_scope, user.id, effective_dept_id
        )
        rag_context = GraphRAGService(self.db).build_chat_context(
            message, user.id, effective_dept_id
        )

        user_context = self._build_user_context(user, access_scope)
        user_prompt = self._build_user_prompt(
            user_context=user_context,
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
            metadata_json={
                "month": month,
                "department_id": effective_dept_id,
                "access_scope": access_scope,
            },
        )

        if not previous_user_messages:
            title = self._generate_title(message)
            conversation = self.repo.update_title(conversation, title)

        try:
            answer = self.llm.complete(
                user_prompt, system_prompt=self._load_system_prompt()
            )
        except Exception:
            answer = self._fallback_answer(intent, data)

        assistant_message = self.repo.add_message(
            conversation.conversation_id,
            role="assistant",
            content=answer,
            intent=intent,
            metadata_json={"structured_data": data, "sources": sources},
        )

        self.db.add(
            ChatLog(
                user_id=user.id,
                question=message,
                intent=intent,
                answer=answer,
                sources_json=sources,
            )
        )
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

    # ── Intent detection ─────────────────────────────────────────────────────

    def detect_intent(self, message: str, previous_messages: list | None = None) -> str:
        # LLM Intent Router
        """Detect the intent."""

        system_prompt = INTENT_PROMPT_PATH.read_text(encoding="utf-8")
        history_text = ""
        if previous_messages:
            # Lấy 4 tin nhắn gần nhất để tạo ngữ cảnh
            recent = previous_messages[-4:]
            for m in recent:
                role_str = "Người dùng" if m.role == "user" else "Hệ thống"
                history_text += f"{role_str}: {m.content}\n"

        user_prompt = f"Lịch sử:\n{history_text}\nCâu hỏi mới: {message}\n"

        try:
            # Gọi LLM, bắt buộc trả về JSON
            raw = self.llm.complete(
                user_prompt, system_prompt=system_prompt, expect_json=True
            )
            import json

            data = json.loads(raw)
            intent = data.get("intent", "")

            valid_intents = [
                "MY_KPI",
                "KPI_RISK_USERS",
                "DEPT_SUMMARY",
                "SLOW_DEPARTMENTS",
                "EMPLOYEE_PROFILE",
                "TASK_STATUS",
                "EVIDENCE_EXPLAIN",
                "GENERATE_REPORT",
                "GENERAL_HELP",
            ]
            if intent in valid_intents:
                return intent
        except Exception as error:
            LOGGER.warning(
                "LLM intent router failed; using keyword matching: %s", error
            )

        return self._fallback_detect_intent(message)

    def _fallback_detect_intent(self, message: str) -> str:
        """Return fallback the detect intent."""

        lower = message.lower()

        # KPI cá nhân
        if any(
            k in lower
            for k in [
                "kpi của tôi",
                "điểm của tôi",
                "tôi đạt",
                "kpi bản thân",
                "kết quả kpi",
            ]
        ):
            return "MY_KPI"

        # Nguy cơ / rủi ro KPI
        if any(
            k in lower
            for k in ["nguy cơ", "không đạt", "rủi ro", "kpi thấp", "ai thấp"]
        ):
            return "KPI_RISK_USERS"

        # Tổng kết đơn vị; vẫn nhận từ khóa cũ để tương thích câu hỏi người dùng.
        if any(
            k in lower
            for k in [
                "tổng kết xóm",
                "tình hình xóm",
                "tổng quan xóm",
                "xóm tôi",
                "tổng kết đơn vị",
            ]
        ):
            return "DEPT_SUMMARY"

        # Đơn vị chậm tiến độ.
        if any(unit in lower for unit in ["xóm", "đơn vị"]) and any(
            k in lower for k in ["chậm", "quá hạn", "trễ", "chậm tiến độ"]
        ):
            return "SLOW_DEPARTMENTS"

        # Hồ sơ cá nhân / giải thích điểm
        if any(
            k in lower
            for k in ["vì sao", "tại sao", "điểm thấp", "giải thích", "lý do"]
        ):
            return "EMPLOYEE_PROFILE"

        # Minh chứng — kiểm tra TRƯỚC nhiệm vụ để tránh xung đột
        if "minh chứng" in lower:
            return "EVIDENCE_EXPLAIN"

        # Nhiệm vụ / tiến độ
        if any(k in lower for k in ["nhiệm vụ", "tiến độ", "công việc", "task"]):
            return "TASK_STATUS"

        # Báo cáo
        if "báo cáo" in lower:
            return "GENERATE_REPORT"

        return "GENERAL_HELP"

    # ── Role-aware structured data ────────────────────────────────────────────

    def _structured_data(
        self,
        intent: str,
        month: str | None,
        access_scope: int,
        user_id: int,
        department_id: int | None,
    ) -> dict:
        """Handle the data."""

        period = month or datetime.now().strftime("%Y-%m")

        if intent == "MY_KPI":
            return self._query_my_kpi(user_id, period)

        if intent == "KPI_RISK_USERS":
            return self._query_kpi_risk(access_scope, user_id, department_id, period)

        if intent == "SLOW_DEPARTMENTS":
            return self._query_slow_departments(access_scope, department_id)

        if intent == "DEPT_SUMMARY":
            return self._query_dept_summary(access_scope, department_id, period)

        if intent == "EMPLOYEE_PROFILE":
            return self._query_employee_profile(
                access_scope, user_id, department_id, period
            )

        if intent == "TASK_STATUS":
            return self._query_task_status(access_scope, user_id, department_id)

        # Add organization totals for general questions.
        user_count_query = self.db.query(func.count(User.id)).filter(
            User.role != "admin"
        )
        department_query = self.db.query(Department.name).filter(
            Department.unit_type.in_(["LEADERSHIP", "UNIT"])
        )
        if access_scope == 1 and department_id:
            user_count_query = user_count_query.filter(
                User.department_id == department_id
            )
            department_query = department_query.filter(Department.id == department_id)
        elif access_scope == 2:
            user_count_query = user_count_query.filter(User.id == user_id)
            department_query = department_query.filter(Department.id == department_id)
        users_count = user_count_query.scalar()
        dept_names = [department_name for (department_name,) in department_query.all()]

        data_res = self._query_task_status(access_scope, user_id, department_id)
        data_res["total_employees"] = users_count
        data_res["total_departments"] = len(dept_names)
        data_res["department_list"] = dept_names
        return data_res

    def _query_my_kpi(self, user_id: int, period: str) -> dict:
        """KPI cá nhân: điểm, phân loại, breakdown chi tiết."""
        score = (
            self.db.query(KPIScore)
            .filter(KPIScore.user_id == user_id, KPIScore.period_month == period)
            .first()
        )
        if not score:
            return {
                "period": period,
                "my_kpi": None,
                "message": "Chưa có dữ liệu KPI cho kỳ này",
            }
        return {
            "period": period,
            "my_kpi": {
                "total_score": score.total_score,
                "classification": score.classification,
                "risk_level": score.risk_level,
                "breakdown": score.breakdown_json,
                "ai_explanation": score.ai_explanation,
            },
        }

    def _query_kpi_risk(
        self, access_scope: int, user_id: int, dept_id: int | None, period: str
    ) -> dict:
        """Return KPI risks within organization, unit, or personal scope."""
        q = (
            self.db.query(
                User.full_name,
                Department.name,
                KPIScore.total_score,
                KPIScore.risk_level,
            )
            .join(KPIScore, KPIScore.user_id == User.id)
            .outerjoin(Department, Department.id == User.department_id)
            .filter(
                KPIScore.period_month == period,
                KPIScore.risk_level.in_(["HIGH", "MEDIUM"]),
            )
        )
        if access_scope == 1 and dept_id:
            q = q.filter(User.department_id == dept_id)
        elif access_scope == 2:
            q = q.filter(User.id == user_id)

        rows = q.order_by(KPIScore.total_score.asc()).limit(10).all()
        return {
            "period": period,
            "risk_users": [
                dict(name=r[0], department=r[1], score=r[2], risk=r[3]) for r in rows
            ],
        }

    def _query_slow_departments(
        self, access_scope: int, dept_id: int | None
    ) -> dict:
        """Return units with overdue tasks within the authorized scope."""
        if access_scope == 2:
            return {
                "slow_departments": [],
                "message": "Bạn không có quyền xem thống kê nhiệm vụ toàn đơn vị.",
            }

        q = (
            self.db.query(Department.name, func.count(Task.id))
            .join(Task, Task.department_id == Department.id)
            .filter(Task.status == "OVERDUE")
            .group_by(Department.name)
        )
        if access_scope == 1 and dept_id:
            q = q.filter(Department.id == dept_id)
        rows = q.order_by(func.count(Task.id).desc()).all()
        return {
            "slow_departments": [
                {"department": r[0], "overdue_tasks": r[1]} for r in rows
            ]
        }

    def _query_dept_summary(
        self, access_scope: int, dept_id: int | None, period: str
    ) -> dict:
        """Return task and KPI summary for the authorized unit scope."""
        if access_scope == 2:
            return {
                "dept_summary": None,
                "message": "Bạn không có quyền xem tổng quan dữ liệu toàn đơn vị.",
            }

        dept_filter = []
        if access_scope == 1 and dept_id:
            dept_filter = [Task.department_id == dept_id]

        task_rows = (
            self.db.query(Task.status, func.count(Task.id))
            .filter(*dept_filter)
            .group_by(Task.status)
            .all()
        )
        task_summary = {status: count for status, count in task_rows}

        # KPI trung bình trong phòng
        kpi_q = self.db.query(func.avg(KPIScore.total_score)).filter(
            KPIScore.period_month == period
        )
        if access_scope == 1 and dept_id:
            kpi_q = kpi_q.join(User, User.id == KPIScore.user_id).filter(
                User.department_id == dept_id
            )
        avg_kpi = kpi_q.scalar()

        return {
            "period": period,
            "dept_summary": {
                "task_by_status": task_summary,
                "avg_kpi": round(float(avg_kpi), 2) if avg_kpi else None,
            },
        }

    def _query_employee_profile(
        self, access_scope: int, user_id: int, dept_id: int | None, period: str
    ) -> dict:
        """Hồ sơ nhân viên — Lãnh đạo xem nhân viên mình quản; Chuyên viên chỉ xem bản thân."""
        if access_scope == 2:
            # Thành viên chỉ xem bản thân.
            rows = (
                self.db.query(
                    User.full_name,
                    KPIScore.total_score,
                    KPIScore.classification,
                    KPIScore.risk_level,
                    KPIScore.ai_explanation,
                )
                .join(KPIScore, KPIScore.user_id == User.id)
                .filter(KPIScore.period_month == period, User.id == user_id)
                .all()
            )
        else:
            q = (
                self.db.query(
                    User.full_name,
                    KPIScore.total_score,
                    KPIScore.classification,
                    KPIScore.risk_level,
                    KPIScore.ai_explanation,
                )
                .join(KPIScore, KPIScore.user_id == User.id)
                .filter(KPIScore.period_month == period)
            )
            if access_scope == 1 and dept_id:
                q = q.filter(User.department_id == dept_id)
            rows = q.order_by(KPIScore.total_score.asc()).limit(10).all()

        return {
            "period": period,
            "employee_profiles": [
                {
                    "name": r[0],
                    "score": r[1],
                    "classification": r[2],
                    "risk": r[3],
                    "ai_note": r[4],
                }
                for r in rows
            ],
        }

    def _query_task_status(
        self, access_scope: int, user_id: int, dept_id: int | None
    ) -> dict:
        """Return task totals within organization, unit, or personal scope."""
        if access_scope == 2:
            # Thành viên: nhiệm vụ được giao cho mình.
            rows = (
                self.db.query(Task.status, func.count(Task.id))
                .join(TaskAssignment, TaskAssignment.task_id == Task.id)
                .filter(TaskAssignment.user_id == user_id)
                .group_by(Task.status)
                .all()
            )
            return {"scope": "personal", "task_status": {s: c for s, c in rows}}

        if access_scope == 1 and dept_id:
            rows = (
                self.db.query(Task.status, func.count(Task.id))
                .filter(Task.department_id == dept_id)
                .group_by(Task.status)
                .all()
            )
            return {"scope": "unit", "task_status": {s: c for s, c in rows}}

        # Admin: toàn tổ chức.
        rows = (
            self.db.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
        )
        return {"scope": "organization", "task_status": {s: c for s, c in rows}}

    # ── Prompt building ───────────────────────────────────────────────────────

    def _access_scope(self, user: User) -> int:
        """Map organization roles to organization, unit, or personal data scope."""

        if is_admin(user) or user.organization_role == LEADERSHIP_ROLE:
            return 0
        if user.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}:
            return 1
        return 2

    def _build_user_context(self, user: User, access_scope: int) -> str:
        """Build explicit Vietnamese identity and authorization context."""

        dept_name = user.department.name if user.department else "Không xác định"
        role_label = {
            LEADERSHIP_ROLE: "Lãnh đạo HĐND, UBND xã",
            UNIT_HEAD_ROLE: "Trưởng đơn vị",
            UNIT_DEPUTY_ROLE: "Phó trưởng đơn vị",
            "SPECIALIST": "Công chức chuyên môn, nghiệp vụ",
            "OUT_OF_SCOPE": "Viên chức chưa thuộc phạm vi KPI",
        }.get(user.organization_role, "Cán bộ")
        scope_label = {
            0: "Toàn tổ chức",
            1: f"Đơn vị {dept_name}",
            2: "Chỉ dữ liệu cá nhân",
        }[access_scope]
        return (
            f"Người dùng: {user.full_name}\n"
            f"Chức danh: {user.position_title or role_label}\n"
            f"Vai trò tổ chức: {role_label}\n"
            f"Đơn vị: {dept_name}\n"
            f"Phạm vi truy cập dữ liệu: {scope_label}"
        )

    def _get_or_create_conversation(
        self, conversation_id: int | None, user_id: int | None
    ) -> Conversation:
        """Return the or create conversation."""

        if conversation_id:
            conversation = self.repo.get_active(conversation_id, user_id)
            if conversation:
                return conversation
        return self.repo.create(user_id=user_id)

    def _load_system_prompt(self) -> str:
        """Load the system prompt."""

        return PROMPT_PATH.read_text(encoding="utf-8")

    def _build_user_prompt(
        self,
        user_context: str,
        history: str,
        conversation_summary: str,
        message: str,
        structured_data: dict,
        rag_context: dict,
    ) -> str:
        """Build the user prompt."""

        return (
            "THÔNG TIN NGƯỜI DÙNG\n\n"
            f"{user_context}\n\n"
            "---\n\n"
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
            "- Trả lời phù hợp với cấp bậc và phạm vi quản lý của người dùng.\n"
            "- Không bịa số liệu.\n"
            "- Không bỏ qua ngữ cảnh hội thoại trước đó.\n"
        )

    def _format_history(self, messages: list) -> str:
        """Format the history."""

        rows = []
        for item in messages:
            label = {"user": "User", "assistant": "Assistant", "system": "System"}.get(
                item.role, item.role
            )
            rows.append(f"{label}: {item.content}")
        return "\n\n".join(rows)

    def _generate_title(self, first_message: str) -> str:
        """Generate the title."""

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
        """Summarize the if needed."""

        count = self.repo.count_messages(conversation_id)
        if count < 20 or count % 20 != 0:
            return
        messages = self.repo.list_messages(conversation_id, limit=20)
        current_summary = self.repo.get_summary(conversation_id)
        prompt = (
            "Tóm tắt hội thoại dưới đây để dùng làm memory cho AI Copilot.\n"
            "Yêu cầu: ngắn gọn, tiếng Việt, giữ lại chủ đề chính, cá nhân/đơn vị được nhắc và câu hỏi đang theo đuổi.\n\n"
            f"Tóm tắt hiện tại:\n{current_summary.summary if current_summary else '(chưa có)'}\n\n"
            f"Tin nhắn gần đây:\n{self._format_history(messages)}"
        )
        try:
            summary = self.llm.complete(prompt)
        except Exception:
            summary = self._format_history(messages)[-1800:]
        self.repo.upsert_summary(conversation_id, summary.strip())

    # ── Fallback answers ──────────────────────────────────────────────────────

    def _fallback_answer(self, intent: str, data: dict) -> str:
        """Return fallback the answer."""

        if intent == "MY_KPI":
            kpi = data.get("my_kpi")
            if not kpi:
                return "Chưa có dữ liệu KPI của bạn cho kỳ này."
            return f"Điểm theo dõi tháng của bạn: {kpi['total_score']} điểm — Mức tham chiếu: {kpi['classification']} — Rủi ro vận hành: {kpi['risk_level']}."
        if intent == "KPI_RISK_USERS":
            names = [item["name"] for item in data.get("risk_users", [])[:5]]
            return "Nhóm có nguy cơ không đạt KPI: " + (
                ", ".join(names) if names else "chưa có dữ liệu rủi ro."
            )
        if intent == "SLOW_DEPARTMENTS":
            rows = data.get("slow_departments", [])
            if not rows:
                return "Chưa ghi nhận đơn vị chậm tiến độ trong dữ liệu hiện có."
            return "Đơn vị chậm tiến độ: " + ", ".join(
                f"{r['department']} ({r['overdue_tasks']} nhiệm vụ quá hạn)"
                for r in rows[:5]
            )
        return "Đã lấy được dữ liệu nghiệp vụ, nhưng LLM chưa phản hồi. Vui lòng kiểm tra cấu hình LLM, quota hoặc kết nối mạng."

    # ── Serializers ───────────────────────────────────────────────────────────

    def _conversation_to_dict(self, conversation: Conversation) -> dict:
        """Handle the to dict."""

        return {
            "conversation_id": conversation.conversation_id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "is_deleted": conversation.is_deleted,
        }

    def _message_to_dict(self, message) -> dict:
        """Handle the to dict."""

        return {
            "message_id": message.message_id,
            "conversation_id": message.conversation_id,
            "role": message.role,
            "content": message.content,
            "intent": message.intent,
            "metadata_json": message.metadata_json or {},
            "created_at": message.created_at,
        }
