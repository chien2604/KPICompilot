import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_layer.llm_client import get_llm_client
from ai_layer.rag.graph_rag_service import GraphRAGService
from db.models.chat import ChatLog
from db.models.departments import Department
from db.models.kpi import KPIScore
from db.models.tasks import Task, TaskAssignment
from db.models.users import User


class ChatbotService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm = get_llm_client()

    def answer(self, user_id: int | None, message: str, month: str | None, department_id: int | None) -> dict:
        intent = self.detect_intent(message)
        data = self._structured_data(intent, month, department_id)
        rag_context = GraphRAGService(self.db).build_chat_context(message, None, department_id)
        prompt = (
            "Trả lời câu hỏi lãnh đạo bằng tiếng Việt, không bịa số liệu.\n"
            f"Câu hỏi: {message}\n"
            f"Intent: {intent}\n"
            f"Dữ liệu: {json.dumps(data, ensure_ascii=False)}\n"
            f"Context GraphRAG: {json.dumps(rag_context, ensure_ascii=False)}"
        )
        try:
            answer = self.llm.complete(prompt)
        except Exception:
            answer = self._fallback_answer(intent, data)
        sources = rag_context.get("vectors", [])[:3]
        self.db.add(ChatLog(user_id=user_id, question=message, intent=intent, answer=answer, sources_json=sources))
        self.db.commit()
        return {"answer": answer, "intent": intent, "data": data, "sources": sources}

    def detect_intent(self, message: str) -> str:
        lower = message.lower()
        if "nguy cơ" in lower or "không đạt" in lower or "rủi ro" in lower:
            return "KPI_RISK_USERS"
        if "phòng" in lower and ("chậm" in lower or "quá hạn" in lower):
            return "SLOW_DEPARTMENTS"
        if "vì sao" in lower or "điểm thấp" in lower:
            return "EMPLOYEE_PROFILE"
        if "nhiệm vụ" in lower or "tiến độ" in lower:
            return "TASK_STATUS"
        if "minh chứng" in lower:
            return "EVIDENCE_EXPLAIN"
        if "báo cáo" in lower:
            return "GENERATE_REPORT"
        return "GENERAL_HELP"

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
        return "Đã lấy được dữ liệu nghiệp vụ, nhưng LLM thật chưa phản hồi. Vui lòng kiểm tra OPENAI_API_KEY, quota hoặc kết nối mạng."
