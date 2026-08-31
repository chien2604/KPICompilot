"""Calculate KPI scores deterministically under Decree 335/2025/NĐ-CP."""

from datetime import datetime

from ai_layer.kpi_explainer import KPIExplainer
from core.organization import LEADERSHIP_ROLE, UNIT_DEPUTY_ROLE, UNIT_HEAD_ROLE
from db.models.kpi import (
    KPIAssessmentInput,
    KPICriterion,
    KPIScore,
    KPITemplate,
    WorkCatalogItem,
)
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from sqlalchemy import or_
from sqlalchemy.orm import Session

MANAGEMENT_ROLES = {LEADERSHIP_ROLE, UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}
MANAGEMENT_METRICS = (
    "unit_result_percent",
    "implementation_percent",
    "cohesion_percent",
)


class KPIEngine:
    """Combine reviewer inputs and task ratios without asking an LLM to score."""

    def __init__(self, database_session: Session) -> None:
        """Store the database session used by all scoring queries."""

        self.database_session = database_session

    def compute_user_score(self, user_id: int, period_month: str) -> dict:
        """Calculate one monthly result using the official 30/70 structure."""

        period_start, period_end = self._period_bounds(period_month)
        user = self.database_session.get(User, user_id)
        if user is None:
            raise ValueError("Không tìm thấy cán bộ.")
        if not user.is_kpi_eligible:
            raise ValueError("Cán bộ chưa thuộc phạm vi tiêu chí KPI hiện hành.")
        template = (
            self.database_session.query(KPITemplate)
            .filter(KPITemplate.code == user.kpi_role_template)
            .first()
        )
        if template is None:
            raise ValueError(f"Chưa cấu hình template KPI {user.kpi_role_template}.")
        criteria = (
            self.database_session.query(KPICriterion)
            .filter(KPICriterion.template_id == template.id)
            .order_by(KPICriterion.sort_order)
            .all()
        )
        assessment = (
            self.database_session.query(KPIAssessmentInput)
            .filter(
                KPIAssessmentInput.user_id == user_id,
                KPIAssessmentInput.period_month == period_month,
            )
            .first()
        )
        common_result = self._common_score(criteria, assessment)
        assignments = self._period_assignments(user_id, period_start, period_end)
        task_result = self._task_result(user, assignments, assessment)
        total_score = round(common_result["score"] + task_result["score"], 2)
        missing_inputs = common_result["missing_inputs"] + task_result["missing_inputs"]
        return {
            "user_id": user_id,
            "period_month": period_month,
            "template_id": template.id,
            "total_score": total_score,
            "classification": self.classify(total_score),
            "risk_level": self.risk_level(total_score),
            "breakdown": [common_result["breakdown"], task_result["breakdown"]],
            "raw_reasons": common_result["reasons"] + task_result["reasons"],
            "formula": task_result["formula"],
            "missing_inputs": missing_inputs,
            "is_complete": not missing_inputs,
            "legal_basis": (
                "Nghị định 335/2025/NĐ-CP và Quyết định 283/QĐ-UBND "
                "ngày 31/05/2026 của UBND xã Nghĩa Lâm"
            ),
        }

    def recompute_and_save(self, user_id: int, period_month: str) -> KPIScore:
        """Recompute, explain the fixed result, and persist one score row."""

        result = self.compute_user_score(user_id, period_month)
        explanation = KPIExplainer().explain(result)
        row = (
            self.database_session.query(KPIScore)
            .filter(KPIScore.user_id == user_id, KPIScore.period_month == period_month)
            .order_by(KPIScore.created_at.desc())
            .first()
        )
        if row is None:
            row = KPIScore(user_id=user_id, period_month=period_month)
            self.database_session.add(row)
        row.template_id = result["template_id"]
        row.total_score = result["total_score"]
        row.classification = result["classification"]
        row.breakdown_json = {
            "breakdown": result["breakdown"],
            "raw_reasons": result["raw_reasons"],
            "formula": result["formula"],
            "missing_inputs": result["missing_inputs"],
            "is_complete": result["is_complete"],
            "legal_basis": result["legal_basis"],
        }
        row.risk_level = result["risk_level"]
        row.ai_explanation = explanation
        self.database_session.commit()
        self.database_session.refresh(row)
        return row

    def classify(self, score: float) -> str:
        """Classify a result using the score bands in Decree 335."""

        if score >= 90:
            return "Hoàn thành xuất sắc nhiệm vụ"
        if score >= 70:
            return "Hoàn thành tốt nhiệm vụ"
        if score >= 50:
            return "Hoàn thành nhiệm vụ"
        return "Không hoàn thành nhiệm vụ"

    def risk_level(self, score: float) -> str:
        """Map final points to the existing operational risk scale."""

        if score >= 85:
            return "LOW"
        if score >= 70:
            return "MEDIUM"
        return "HIGH"

    def _period_bounds(self, period_month: str) -> tuple[datetime, datetime]:
        """Return inclusive start and exclusive end datetimes for a month."""

        period_start = datetime.strptime(period_month, "%Y-%m")
        period_end = (
            period_start.replace(year=period_start.year + 1, month=1)
            if period_start.month == 12
            else period_start.replace(month=period_start.month + 1)
        )
        return period_start, period_end

    def _period_assignments(
        self, user_id: int, period_start: datetime, period_end: datetime
    ) -> list[TaskAssignment]:
        """Load assignments whose deadline or creation date belongs to the month."""

        return (
            self.database_session.query(TaskAssignment)
            .join(Task)
            .filter(
                TaskAssignment.user_id == user_id,
                or_(
                    (Task.deadline >= period_start) & (Task.deadline < period_end),
                    (Task.deadline.is_(None))
                    & (Task.created_at >= period_start)
                    & (Task.created_at < period_end),
                ),
            )
            .all()
        )

    def _common_score(
        self,
        criteria: list[KPICriterion],
        assessment: KPIAssessmentInput | None,
    ) -> dict:
        """Validate and total the 30-point reviewer-entered common criteria."""

        entered_scores = assessment.common_scores_json if assessment else {}
        score = 0.0
        reasons: list[str] = []
        missing_inputs: list[str] = []
        criterion_rows: list[dict] = []
        for criterion in criteria:
            entered_value = entered_scores.get(criterion.criterion_code)
            if entered_value is None:
                value = 0.0
                missing_inputs.append(criterion.criterion_code)
            else:
                value = float(entered_value)
                if value < 0 or value > criterion.max_score:
                    raise ValueError(
                        f"Điểm {criterion.criterion_code} phải từ 0 đến {criterion.max_score}."
                    )
            score += value
            criterion_rows.append(
                {
                    "criterion_code": criterion.criterion_code,
                    "criterion_name": criterion.criterion_name,
                    "max_score": criterion.max_score,
                    "score": value,
                }
            )
        reasons.append(f"Tiêu chí chung được duyệt: {score:.2f}/30 điểm.")
        if missing_inputs:
            reasons.append(
                f"Còn {len(missing_inputs)} tiêu chí chung chưa được người có thẩm quyền chấm."
            )
        return {
            "score": round(score, 2),
            "reasons": reasons,
            "missing_inputs": missing_inputs,
            "breakdown": {
                "group_code": "COMMON",
                "group_name": "Tiêu chí chung",
                "max_score": 30,
                "score": round(score, 2),
                "criteria": criterion_rows,
                "reasons": reasons,
            },
        }

    def _task_result(
        self,
        user: User,
        assignments: list[TaskAssignment],
        assessment: KPIAssessmentInput | None,
    ) -> dict:
        """Calculate quantity, quality, timeliness, and management ratios."""

        total_weight = sum(self._assignment_weight(item) for item in assignments)
        completed_weight = sum(
            self._assignment_weight(item)
            for item in assignments
            if item.task.status == "COMPLETED"
        )
        quantity_ratio = completed_weight / total_weight if total_weight else 0.0
        quality_ratio = self._quality_ratio(assignments, total_weight)
        timeliness_ratio = self._timeliness_ratio(assignments, total_weight)
        ratios = [quantity_ratio, quality_ratio, timeliness_ratio]
        metric_rows = [
            {"code": "a", "name": "Số lượng", "ratio": quantity_ratio},
            {"code": "b", "name": "Chất lượng", "ratio": quality_ratio},
            {"code": "c", "name": "Tiến độ", "ratio": timeliness_ratio},
        ]
        missing_inputs: list[str] = []
        if not assignments:
            missing_inputs.append("TASK_ASSIGNMENTS")
        if user.organization_role in MANAGEMENT_ROLES:
            management_values = (
                assessment.management_metrics_json if assessment else {}
            )
            metric_names = {
                "unit_result_percent": "Kết quả đơn vị/lĩnh vực phụ trách",
                "implementation_percent": "Năng lực tổ chức thực hiện",
                "cohesion_percent": "Đoàn kết nội bộ",
            }
            for metric_code in MANAGEMENT_METRICS:
                entered_value = management_values.get(metric_code)
                if entered_value is None:
                    ratio = 0.0
                    missing_inputs.append(metric_code)
                else:
                    percentage = float(entered_value)
                    if percentage < 0 or percentage > 100:
                        raise ValueError(f"{metric_names[metric_code]} phải từ 0 đến 100%.")
                    ratio = percentage / 100
                ratios.append(ratio)
                metric_rows.append(
                    {
                        "code": metric_code,
                        "name": metric_names[metric_code],
                        "ratio": ratio,
                    }
                )
        average_ratio = sum(ratios) / len(ratios)
        score = round(average_ratio * 70, 2)
        ratio_text = ", ".join(
            f"{item['name']} {item['ratio'] * 100:.1f}%" for item in metric_rows
        )
        reasons = [
            f"Kết quả nhiệm vụ: {score:.2f}/70 điểm ({ratio_text}).",
            f"Khối lượng quy đổi được giao: {total_weight:.2f}; hoàn thành: {completed_weight:.2f}.",
        ]
        formula_codes = "+".join(item["code"] for item in metric_rows)
        return {
            "score": score,
            "reasons": reasons,
            "missing_inputs": missing_inputs,
            "formula": f"R=({formula_codes})/{len(metric_rows)}; điểm kết quả=R×70",
            "breakdown": {
                "group_code": "TASK_RESULT",
                "group_name": "Kết quả thực hiện nhiệm vụ",
                "max_score": 70,
                "score": score,
                "metrics": metric_rows,
                "assigned_conversion_factor": round(total_weight, 2),
                "completed_conversion_factor": round(completed_weight, 2),
                "reasons": reasons,
            },
        }

    def _assignment_weight(self, assignment: TaskAssignment) -> float:
        """Use the approved catalog factor and fall back to an explicit task weight."""

        task = assignment.task
        if task.work_catalog_item_id is not None:
            catalog_item = self.database_session.get(
                WorkCatalogItem, task.work_catalog_item_id
            )
            if catalog_item is not None:
                return max(float(catalog_item.conversion_factor), 0.0)
        return max(float(task.weight or 0), 0.0)

    def _quality_ratio(
        self, assignments: list[TaskAssignment], total_weight: float
    ) -> float:
        """Apply reviewer quality and 25% major-error deductions per product."""

        if total_weight == 0:
            return 0.0
        weighted_quality = 0.0
        for assignment in assignments:
            if assignment.task.status != "COMPLETED":
                continue
            quality_ratio = max(0.0, min(1.0, assignment.quality_percent / 100))
            quality_ratio = max(0.0, quality_ratio - 0.25 * assignment.major_error_count)
            weighted_quality += self._assignment_weight(assignment) * quality_ratio
        return weighted_quality / total_weight

    def _timeliness_ratio(
        self, assignments: list[TaskAssignment], total_weight: float
    ) -> float:
        """Apply the 25% timeliness deduction for each recorded late occurrence."""

        if total_weight == 0:
            return 0.0
        weighted_timeliness = 0.0
        for assignment in assignments:
            if assignment.task.status != "COMPLETED":
                continue
            derived_late_count = 0
            if (
                assignment.task.completed_at
                and assignment.task.deadline
                and assignment.task.completed_at > assignment.task.deadline
            ):
                derived_late_count = 1
            late_count = max(assignment.late_count, derived_late_count)
            timeliness_ratio = max(0.0, 1.0 - 0.25 * late_count)
            weighted_timeliness += self._assignment_weight(assignment) * timeliness_ratio
        return weighted_timeliness / total_weight
