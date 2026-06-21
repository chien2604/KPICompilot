from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from ai_layer.kpi_explainer import KPIExplainer
from db.models.evidences import TaskEvidence
from db.models.kpi import KPICriterion, KPIScore, KPITemplate
from db.models.tasks import Task, TaskAssignment
from db.models.users import User


class KPIEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    def compute_user_score(self, user_id: int, period_month: str) -> dict:
        user = self.db.get(User, user_id)
        if not user:
            raise ValueError("Không tìm thấy cán bộ")
        template = self.db.query(KPITemplate).filter(KPITemplate.code == user.kpi_role_template).first()
        criteria = self.db.query(KPICriterion).filter(KPICriterion.template_id == template.id).all() if template else []
        assignments = (
            self.db.query(TaskAssignment)
            .join(Task)
            .filter(TaskAssignment.user_id == user_id)
            .all()
        )
        task_scores = [self._task_assignment_score(item) for item in assignments]
        avg_task_score = sum(task_scores) / len(task_scores) if task_scores else 75
        overdue_count = sum(1 for item in assignments if item.task.status == "OVERDUE")
        breakdown = self._group_breakdown(criteria, avg_task_score, overdue_count, user.role)
        total = round(sum(item["score"] for item in breakdown), 1)
        result = {
            "user_id": user_id,
            "period_month": period_month,
            "template_id": template.id if template else None,
            "total_score": total,
            "classification": self.classify(total),
            "risk_level": self.risk_level(total),
            "breakdown": breakdown,
            "raw_reasons": [reason for group in breakdown for reason in group["reasons"]],
        }
        return result

    def recompute_and_save(self, user_id: int, period_month: str) -> KPIScore:
        result = self.compute_user_score(user_id, period_month)
        explanation = KPIExplainer().explain(result)
        row = (
            self.db.query(KPIScore)
            .filter(KPIScore.user_id == user_id, KPIScore.period_month == period_month)
            .order_by(KPIScore.created_at.desc())
            .first()
        )
        if not row:
            row = KPIScore(user_id=user_id, period_month=period_month)
            self.db.add(row)
        row.template_id = result["template_id"]
        row.total_score = result["total_score"]
        row.classification = result["classification"]
        row.breakdown_json = {"breakdown": result["breakdown"], "raw_reasons": result["raw_reasons"]}
        row.risk_level = result["risk_level"]
        row.ai_explanation = explanation
        self.db.commit()
        self.db.refresh(row)
        return row

    def classify(self, score: float) -> str:
        if score >= 90:
            return "Hoàn thành xuất sắc nhiệm vụ"
        if score >= 80:
            return "Hoàn thành tốt nhiệm vụ"
        if score >= 65:
            return "Hoàn thành nhiệm vụ"
        return "Không hoàn thành nhiệm vụ"

    def risk_level(self, score: float) -> str:
        if score >= 85:
            return "LOW"
        if score >= 70:
            return "MEDIUM"
        return "HIGH"

    def _task_assignment_score(self, assignment: TaskAssignment) -> float:
        task = assignment.task
        status_factor = {"COMPLETED": 1.0, "IN_PROGRESS": 0.72, "NOT_STARTED": 0.35, "OVERDUE": 0.45}.get(task.status, 0.6)
        doc_factor = {"A": 1.08, "B": 1.0, "C": 0.94, "D": 0.88}.get(task.document_type, 0.94)
        evidence = self.db.query(TaskEvidence).filter(TaskEvidence.task_id == task.id).order_by(TaskEvidence.created_at.desc()).first()
        evidence_factor = ((evidence.ai_relevance_score or 65) / 100) if evidence else 0.72
        base = (assignment.leader_score or assignment.self_score or assignment.progress_percent or 70) / 100
        return max(0, min(100, 100 * (0.45 * status_factor + 0.25 * base + 0.2 * evidence_factor + 0.1 * doc_factor)))

    def _group_breakdown(self, criteria: list[KPICriterion], avg_task_score: float, overdue_count: int, role: str) -> list[dict]:
        grouped: dict[str, dict] = defaultdict(lambda: {"max_score": 0, "criteria": []})
        for criterion in criteria:
            grouped[criterion.group_name]["max_score"] += criterion.max_score
            grouped[criterion.group_name]["criteria"].append(criterion.criterion_name)
        if not grouped:
            grouped["Kết quả công việc"] = {"max_score": 40, "criteria": []}
            grouped["Tiến độ"] = {"max_score": 20, "criteria": []}
            grouped["Kỷ luật thái độ"] = {"max_score": 15, "criteria": []}
            grouped["Phối hợp hỗ trợ"] = {"max_score": 15, "criteria": []}
            grouped["Phát triển năng lực"] = {"max_score": 10, "criteria": []}
        rows = []
        for group_name, data in grouped.items():
            max_score = float(data["max_score"])
            name = group_name.lower()
            if "kết quả" in name:
                ratio = avg_task_score / 100
                reasons = [f"Điểm chất lượng minh chứng và kết quả công việc trung bình đạt {avg_task_score:.1f}/100."]
            elif "tiến độ" in name:
                ratio = max(0.4, 1 - overdue_count * 0.15)
                if overdue_count > 0:
                    reasons = [f"Bị trừ điểm do có {overdue_count} nhiệm vụ quá hạn."]
                else:
                    reasons = ["100% nhiệm vụ đảm bảo đúng tiến độ yêu cầu."]
            elif "kỷ luật" in name:
                ratio = 0.95
                reasons = ["Chấp hành tốt nội quy, không vi phạm kỷ luật đạo đức công vụ."]
            elif "phối hợp" in name:
                ratio = 0.9
                reasons = ["Có tinh thần trách nhiệm, phối hợp tốt với các phòng ban liên quan."]
            else:
                ratio = 0.85
                reasons = ["Tích cực học hỏi, cải tiến phương pháp làm việc và nâng cao nghiệp vụ."]
            rows.append({"group_name": group_name, "max_score": max_score, "score": round(max_score * ratio, 1), "reasons": reasons})
        return rows
