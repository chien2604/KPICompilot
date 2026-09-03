"""Calculate KPI scores deterministically under Decree 335/2025/NĐ-CP."""

from datetime import datetime

from ai_layer.kpi_explainer import KPIExplainer
from core.organization import SPECIALIST_ROLE, UNIT_DEPUTY_ROLE, UNIT_HEAD_ROLE
from db.models.evidences import TaskEvidence
from db.models.kpi import (
    KPIAssessmentInput,
    KPICriterion,
    KPIScore,
    KPITemplate,
)
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from sqlalchemy import or_
from sqlalchemy.orm import Session

MANAGEMENT_ROLES = {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}


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
        task_result = self._task_result(
            user, assignments, assessment, period_month
        )
        total_score = round(common_result["score"] + task_result["score"], 2)
        missing_inputs = common_result["missing_inputs"] + task_result["missing_inputs"]
        return {
            "user_id": user_id,
            "period_month": period_month,
            "template_id": template.id,
            "total_score": total_score,
            "classification": self.reference_level(total_score),
            "reference_level": self.reference_level(total_score),
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
        row.score_status = "PENDING_CONFIRMATION"
        row.confirmed_by = None
        row.confirmed_at = None
        self.database_session.commit()
        self.database_session.refresh(row)
        return row

    def reference_level(self, score: float) -> str:
        """Return a monthly tracking band without claiming annual classification."""

        if score >= 90:
            return "Mức tham chiếu 90-100"
        if score >= 70:
            return "Mức tham chiếu 70-89"
        if score >= 50:
            return "Mức tham chiếu 50-69"
        return "Mức tham chiếu dưới 50"

    def risk_level(self, score: float) -> str:
        """Map final points to the existing operational risk scale."""

        if score >= 85:
            return "LOW"
        if score >= 70:
            return "MEDIUM"
        return "HIGH"

    def _period_bounds(self, period_month: str) -> tuple[datetime, datetime]:
        """Return inclusive start and exclusive end for a month or quarter."""

        if "-Q" in period_month:
            year_text, quarter_text = period_month.split("-Q")
            start_month = (int(quarter_text) - 1) * 3 + 1
            period_start = datetime(int(year_text), start_month, 1)
            end_month = start_month + 3
            period_end = (
                datetime(int(year_text) + 1, 1, 1)
                if end_month > 12
                else datetime(int(year_text), end_month, 1)
            )
            return period_start, period_end
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

        entered_scores = assessment.reviewed_scores_json if assessment else {}
        self_scores = assessment.self_scores_json if assessment else {}
        score = 0.0
        reasons: list[str] = []
        missing_inputs: list[str] = []
        criterion_rows: list[dict] = []
        for criterion in criteria:
            entered_value = entered_scores.get(criterion.criterion_code)
            if criterion.criterion_code not in self_scores:
                missing_inputs.append(f"SELF:{criterion.criterion_code}")
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
        period_month: str,
    ) -> dict:
        """Calculate quantity, quality, timeliness, and management ratios."""

        total_weight = sum(self._assignment_weight(item) for item in assignments)
        completed_weight = sum(
            self._assignment_weight(item)
            for item in assignments
            if self._is_verified_output(item)
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
            unit_ratio = self._managed_user_ratio(user, period_month)
            if unit_ratio is None:
                unit_ratio = 0.0
                missing_inputs.append("d")
            ratios.append(unit_ratio)
            metric_rows.append(
                {
                    "code": "d",
                    "name": "Kết quả nhân sự thuộc phạm vi quản lý",
                    "ratio": unit_ratio,
                }
            )
            management_values = assessment.management_review_json if assessment else {}
            management_fields = (
                ("implementation_level", "Năng lực tổ chức thực hiện"),
                ("cohesion_level", "Đoàn kết nội bộ"),
            )
            for code, name in management_fields:
                level = management_values.get(code)
                if level not in {"FULL", "PARTIAL"}:
                    ratio = 0.0
                    missing_inputs.append(code)
                else:
                    ratio = 1.0 if level == "FULL" else 0.5
                ratios.append(ratio)
                metric_rows.append(
                    {
                        "code": "đ" if code == "implementation_level" else "e",
                        "name": name,
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
        if task.conversion_factor_snapshot is not None:
            return max(float(task.conversion_factor_snapshot), 0.0)
        return max(float(task.weight or 0), 0.0)

    def _quality_ratio(
        self, assignments: list[TaskAssignment], total_weight: float
    ) -> float:
        """Apply reviewer quality and 25% major-error deductions per product."""

        if total_weight == 0:
            return 0.0
        weighted_quality = 0.0
        for assignment in assignments:
            if not self._is_verified_output(assignment):
                continue
            quality_ratio = 1.0 if assignment.quality_status == "PASS" else 0.0
            if not assignment.objective_quality_exception:
                quality_ratio = max(
                    0.0,
                    quality_ratio - 0.25 * assignment.major_error_count,
                )
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
            if not self._is_verified_output(assignment):
                continue
            derived_late_count = 0
            if (
                assignment.submitted_at
                and assignment.task.deadline
                and assignment.submitted_at > assignment.task.deadline
            ):
                derived_late_count = 1
            late_count = max(assignment.late_count, derived_late_count)
            timeliness_ratio = (
                1.0
                if assignment.objective_delay_exception
                else max(0.0, 1.0 - 0.25 * late_count)
            )
            weighted_timeliness += self._assignment_weight(assignment) * timeliness_ratio
        return weighted_timeliness / total_weight

    def _is_verified_output(self, assignment: TaskAssignment) -> bool:
        """Require both human assignment verification and a verified output record."""

        if assignment.status != "VERIFIED":
            return False
        return self.database_session.query(TaskEvidence.id).filter(
            TaskEvidence.assignment_id == assignment.id,
            TaskEvidence.verification_status == "VERIFIED",
        ).first() is not None

    def _managed_user_ratio(
        self,
        manager: User,
        period_month: str,
    ) -> float | None:
        """Apply the fixed unit-result rule to the manager's confirmed scope."""

        managed_users = self._managed_users(manager)
        if not managed_users:
            return None
        managed_user_ids = [user.id for user in managed_users]
        score_rows = (
            self.database_session.query(
                KPIScore.user_id,
                KPIScore.total_score,
                KPIScore.created_at,
            )
            .filter(
                KPIScore.user_id.in_(managed_user_ids),
                KPIScore.period_month == period_month,
                KPIScore.score_status == "CONFIRMED",
            )
            .order_by(KPIScore.created_at)
            .all()
        )
        latest_scores = {row[0]: float(row[1]) for row in score_rows}
        if len(latest_scores) != len(managed_user_ids):
            return None
        return self._management_result_ratio(list(latest_scores.values()))

    def _managed_users(self, manager: User) -> list[User]:
        """Resolve direct reports for heads and delegated work-area scope for deputies."""

        if manager.organization_role == UNIT_HEAD_ROLE:
            return (
                self.database_session.query(User)
                .filter(
                    User.manager_id == manager.id,
                    User.is_active.is_(True),
                    User.is_kpi_eligible.is_(True),
                )
                .all()
            )
        if manager.organization_role != UNIT_DEPUTY_ROLE:
            return []
        candidates = (
            self.database_session.query(User)
            .filter(
                User.department_id == manager.department_id,
                User.organization_role == SPECIALIST_ROLE,
                User.is_active.is_(True),
                User.is_kpi_eligible.is_(True),
            )
            .all()
        )
        scope = manager.management_scope_json or {}
        if scope.get("all_department"):
            return candidates
        allowed_areas = set(scope.get("work_area_codes", []))
        if not allowed_areas:
            return []
        return [
            user
            for user in candidates
            if allowed_areas.intersection(area.area_code for area in user.work_areas)
        ]

    @staticmethod
    def _management_result_ratio(scores: list[float]) -> float:
        """Return 50% when any managed score is below 50, otherwise 100%."""

        return 0.5 if any(score < 50 for score in scores) else 1.0
