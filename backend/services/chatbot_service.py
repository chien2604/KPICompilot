import json
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_layer.llm_client import get_llm_client
from ai_layer.rag.graph_rag_service import GraphRAGService
from core.permissions import get_user_level
from db.models.chat import ChatLog, Conversation
from db.models.departments import Department
from db.models.kpi import KPIScore
from db.models.tasks import Task, TaskAssignment
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
        user: User,
        message: str,
        month: str | None,
        department_id: int | None,
        conversation_id: int | None = None,
    ) -> dict:
        user_level = get_user_level(user)
        # Nếu caller không truyền department_id, dùng department_id của chính user
        effective_dept_id = department_id or user.department_id

        conversation = self._get_or_create_conversation(conversation_id, user.id)
        previous_messages = self.repo.list_messages(conversation.conversation_id, limit=12)
        previous_user_messages = [m for m in previous_messages if m.role == "user"]
        conversation_summary = ""
        if len(previous_messages) > 10:
            summary = self.repo.get_summary(conversation.conversation_id)
            conversation_summary = summary.summary if summary else ""

        # Sử dụng LLM Intent Router (có fallback về regex)
        intent = self.detect_intent(message, previous_messages=previous_messages)
        data = self._structured_data(intent, month, user_level, user.id, effective_dept_id)
        rag_context = GraphRAGService(self.db).build_chat_context(message, user.id, effective_dept_id)

        user_context = self._build_user_context(user, user_level)
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
            metadata_json={"month": month, "department_id": effective_dept_id, "user_level": user_level},
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

        self.db.add(ChatLog(user_id=user.id, question=message, intent=intent, answer=answer, sources_json=sources))
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
        system_prompt = """Bạn là bộ định tuyến ý định (Intent Router) cho AI Copilot. 
Dựa vào lịch sử hội thoại và câu hỏi mới nhất, hãy phân loại ý định của người dùng vào MỘT trong các mã sau.
CHỈ TRẢ VỀ MÃ Ý ĐỊNH DƯỚI DẠNG JSON, KHÔNG GIẢI THÍCH (ví dụ: {"intent": "MY_KPI"}).

Mã ý định:
MY_KPI: Xem KPI, điểm số, kết quả của bản thân
KPI_RISK_USERS: Xem danh sách nhân viên có nguy cơ không đạt KPI, điểm thấp, cán bộ rủi ro
DEPT_SUMMARY: Xem tổng kết, tình hình chung của một phòng ban
SLOW_DEPARTMENTS: Xem danh sách phòng ban chậm tiến độ, trễ nhiệm vụ, phòng có nhiệm vụ quá hạn
EMPLOYEE_PROFILE: Xem hồ sơ, giải thích nguyên nhân/tại sao một nhân viên có điểm thấp
TASK_STATUS: Xem tình hình, tiến độ, danh sách các nhiệm vụ cụ thể, tại sao nhiệm vụ trễ
EVIDENCE_EXPLAIN: Xem hoặc giải thích minh chứng của một nhiệm vụ, minh chứng chưa duyệt
GENERATE_REPORT: Tạo hoặc xem báo cáo giao ban
GENERAL_HELP: Hỏi đáp chung.

Quy tắc bắt buộc (Rất quan trọng):
1. Nếu câu hỏi có từ "minh chứng", bắt buộc là EVIDENCE_EXPLAIN.
2. Nếu hỏi "Tại sao nhiệm vụ...", bắt buộc là TASK_STATUS.
3. Nếu hỏi "Tại sao nhân viên/anh A/chị B...", bắt buộc là EMPLOYEE_PROFILE.
4. Nếu người dùng hỏi câu tiếp nối ("Còn phòng Thanh tra thì sao?", "Người đó điểm bao nhiêu?"), hãy tham chiếu chủ đề của câu trước đó để chọn intent tương tự (Ví dụ: câu trước hỏi "phòng nào trễ" (SLOW_DEPARTMENTS) -> "còn phòng X" -> SLOW_DEPARTMENTS).
"""
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
            raw = self.llm.complete(user_prompt, system_prompt=system_prompt, expect_json=True)
            import json
            data = json.loads(raw)
            intent = data.get("intent", "")
            
            valid_intents = ["MY_KPI", "KPI_RISK_USERS", "DEPT_SUMMARY", "SLOW_DEPARTMENTS", 
                             "EMPLOYEE_PROFILE", "TASK_STATUS", "EVIDENCE_EXPLAIN", 
                             "GENERATE_REPORT", "GENERAL_HELP"]
            if intent in valid_intents:
                return intent
        except Exception as e:
            print(f"[WARN] LLM Intent Router failed: {e}. Fallback to keyword matching.")
            
        return self._fallback_detect_intent(message)

    def _fallback_detect_intent(self, message: str) -> str:
        lower = message.lower()

        # KPI cá nhân
        if any(k in lower for k in ["kpi của tôi", "điểm của tôi", "tôi đạt", "kpi bản thân", "kết quả kpi"]):
            return "MY_KPI"

        # Nguy cơ / rủi ro KPI
        if any(k in lower for k in ["nguy cơ", "không đạt", "rủi ro", "kpi thấp", "ai thấp"]):
            return "KPI_RISK_USERS"

        # Tổng kết phòng
        if any(k in lower for k in ["tổng kết phòng", "tình hình phòng", "tổng quan phòng", "phòng tôi"]):
            return "DEPT_SUMMARY"

        # Phòng ban chậm
        if "phòng" in lower and any(k in lower for k in ["chậm", "quá hạn", "trễ", "chậm tiến độ"]):
            return "SLOW_DEPARTMENTS"

        # Hồ sơ cá nhân / giải thích điểm
        if any(k in lower for k in ["vì sao", "tại sao", "điểm thấp", "giải thích", "lý do"]):
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
        user_level: int,
        user_id: int,
        department_id: int | None,
    ) -> dict:
        period = month or "2026-06"

        if intent == "MY_KPI":
            return self._query_my_kpi(user_id, period)

        if intent == "KPI_RISK_USERS":
            return self._query_kpi_risk(user_level, user_id, department_id, period)

        if intent == "SLOW_DEPARTMENTS":
            return self._query_slow_departments(user_level, department_id)

        if intent == "DEPT_SUMMARY":
            return self._query_dept_summary(user_level, department_id, period)

        if intent == "EMPLOYEE_PROFILE":
            return self._query_employee_profile(user_level, user_id, department_id, period)

        if intent == "TASK_STATUS":
            return self._query_task_status(user_level, user_id, department_id)

        # Thêm đếm số nhân viên, số phòng ban và danh sách tên phòng ban thực tế vào data trả về
        users_count = self.db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar()
        depts = self.db.query(Department.name).all()
        dept_names = [d[0] for d in depts]

        data_res = self._query_task_status(user_level, user_id, department_id)
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
            return {"period": period, "my_kpi": None, "message": "Chưa có dữ liệu KPI cho kỳ này"}
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

    def _query_kpi_risk(self, level: int, user_id: int, dept_id: int | None, period: str) -> dict:
        """Cán bộ có nguy cơ không đạt KPI — scope theo level."""
        q = (
            self.db.query(User.full_name, Department.name, KPIScore.total_score, KPIScore.risk_level)
            .join(KPIScore, KPIScore.user_id == User.id)
            .outerjoin(Department, Department.id == User.department_id)
            .filter(KPIScore.period_month == period, KPIScore.risk_level.in_(["HIGH", "MEDIUM"]))
        )
        if level >= 3 and dept_id:
            # Trưởng/Phó phòng: chỉ phòng mình
            q = q.filter(User.department_id == dept_id)
        elif level == 5:
            # Chuyên viên: chỉ bản thân
            q = q.filter(User.id == user_id)
        # Level 1-2: toàn Sở — không filter thêm

        rows = q.order_by(KPIScore.total_score.asc()).limit(10).all()
        return {"period": period, "risk_users": [dict(name=r[0], department=r[1], score=r[2], risk=r[3]) for r in rows]}

    def _query_slow_departments(self, level: int, dept_id: int | None) -> dict:
        """Danh sách phòng có nhiệm vụ quá hạn."""
        if level == 5:
            return {"slow_departments": [], "message": "Bạn không có quyền xem thống kê nhiệm vụ của toàn phòng/toàn cơ quan."}

        q = (
            self.db.query(Department.name, func.count(Task.id))
            .join(Task, Task.department_id == Department.id)
            .filter(Task.status == "OVERDUE")
            .group_by(Department.name)
        )
        if level in [3, 4] and dept_id:
            q = q.filter(Department.id == dept_id)
        rows = q.order_by(func.count(Task.id).desc()).all()
        return {"slow_departments": [{"department": r[0], "overdue_tasks": r[1]} for r in rows]}

    def _query_dept_summary(self, level: int, dept_id: int | None, period: str) -> dict:
        """Tổng quan phòng ban: nhiệm vụ + KPI trung bình."""
        if level == 5:
            return {"dept_summary": None, "message": "Bạn không có quyền xem tổng quan dữ liệu của toàn phòng."}

        dept_filter = []
        if level in [3, 4] and dept_id:
            dept_filter = [Task.department_id == dept_id]

        task_rows = (
            self.db.query(Task.status, func.count(Task.id))
            .filter(*dept_filter)
            .group_by(Task.status)
            .all()
        )
        task_summary = {status: count for status, count in task_rows}

        # KPI trung bình trong phòng
        kpi_q = self.db.query(func.avg(KPIScore.total_score)).filter(KPIScore.period_month == period)
        if level >= 3 and dept_id:
            kpi_q = kpi_q.join(User, User.id == KPIScore.user_id).filter(User.department_id == dept_id)
        avg_kpi = kpi_q.scalar()

        return {
            "period": period,
            "dept_summary": {
                "task_by_status": task_summary,
                "avg_kpi": round(float(avg_kpi), 2) if avg_kpi else None,
            },
        }

    def _query_employee_profile(self, level: int, user_id: int, dept_id: int | None, period: str) -> dict:
        """Hồ sơ nhân viên — Lãnh đạo xem nhân viên mình quản; Chuyên viên chỉ xem bản thân."""
        if level == 5:
            # Chuyên viên chỉ xem bản thân
            rows = (
                self.db.query(User.full_name, KPIScore.total_score, KPIScore.classification, KPIScore.risk_level, KPIScore.ai_explanation)
                .join(KPIScore, KPIScore.user_id == User.id)
                .filter(KPIScore.period_month == period, User.id == user_id)
                .all()
            )
        else:
            q = (
                self.db.query(User.full_name, KPIScore.total_score, KPIScore.classification, KPIScore.risk_level, KPIScore.ai_explanation)
                .join(KPIScore, KPIScore.user_id == User.id)
                .filter(KPIScore.period_month == period)
            )
            if level >= 3 and dept_id:
                q = q.filter(User.department_id == dept_id)
            rows = q.order_by(KPIScore.total_score.asc()).limit(10).all()

        return {
            "period": period,
            "employee_profiles": [
                {"name": r[0], "score": r[1], "classification": r[2], "risk": r[3], "ai_note": r[4]}
                for r in rows
            ],
        }

    def _query_task_status(self, level: int, user_id: int, dept_id: int | None) -> dict:
        """Tổng kết nhiệm vụ — scope theo level."""
        if level == 5:
            # Chuyên viên: nhiệm vụ được giao cho mình
            rows = (
                self.db.query(Task.status, func.count(Task.id))
                .join(TaskAssignment, TaskAssignment.task_id == Task.id)
                .filter(TaskAssignment.user_id == user_id)
                .group_by(Task.status)
                .all()
            )
            return {"scope": "personal", "task_status": {s: c for s, c in rows}}

        if level >= 3 and dept_id:
            # Trưởng/Phó phòng: nhiệm vụ phòng mình
            rows = (
                self.db.query(Task.status, func.count(Task.id))
                .filter(Task.department_id == dept_id)
                .group_by(Task.status)
                .all()
            )
            return {"scope": "department", "task_status": {s: c for s, c in rows}}

        # Lãnh đạo cấp cao: toàn Sở
        rows = self.db.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
        return {"scope": "org_wide", "task_status": {s: c for s, c in rows}}

    # ── Prompt building ───────────────────────────────────────────────────────

    def _build_user_context(self, user: User, user_level: int) -> str:
        dept_name = user.department.name if user.department else "Không xác định"
        level_label = {1: "Giám đốc Sở", 2: "Phó Giám đốc Sở", 3: "Trưởng phòng", 4: "Phó phòng", 5: "Chuyên viên"}.get(user_level, "Không xác định")
        return (
            f"Người dùng: {user.full_name}\n"
            f"Chức danh: {user.position_title or level_label}\n"
            f"Phòng ban: {dept_name}\n"
            f"Phạm vi truy cập dữ liệu: {'Toàn Sở' if user_level <= 2 else f'Phòng {dept_name}' if user_level <= 4 else 'Chỉ cá nhân'}"
        )

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
        user_context: str,
        history: str,
        conversation_summary: str,
        message: str,
        structured_data: dict,
        rag_context: dict,
    ) -> str:
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

    # ── Fallback answers ──────────────────────────────────────────────────────

    def _fallback_answer(self, intent: str, data: dict) -> str:
        if intent == "MY_KPI":
            kpi = data.get("my_kpi")
            if not kpi:
                return "Chưa có dữ liệu KPI của bạn cho kỳ này."
            return f"KPI của bạn kỳ này: {kpi['total_score']} điểm — Phân loại: {kpi['classification']} — Rủi ro: {kpi['risk_level']}."
        if intent == "KPI_RISK_USERS":
            names = [item["name"] for item in data.get("risk_users", [])[:5]]
            return "Nhóm có nguy cơ không đạt KPI: " + (", ".join(names) if names else "chưa có dữ liệu rủi ro.")
        if intent == "SLOW_DEPARTMENTS":
            rows = data.get("slow_departments", [])
            if not rows:
                return "Chưa ghi nhận phòng ban chậm tiến độ trong dữ liệu hiện có."
            return "Phòng chậm tiến độ: " + ", ".join(f"{r['department']} ({r['overdue_tasks']} nhiệm vụ quá hạn)" for r in rows[:5])
        return "Đã lấy được dữ liệu nghiệp vụ, nhưng LLM chưa phản hồi. Vui lòng kiểm tra cấu hình LLM, quota hoặc kết nối mạng."

    # ── Serializers ───────────────────────────────────────────────────────────

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
