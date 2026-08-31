from ai_layer.report_generator import ReportGenerator
from db.models.departments import Department
from db.models.kpi import KPIScore
from db.models.reports import Report
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from sqlalchemy import func
from sqlalchemy.orm import Session


class ReportService:
    """Collect scoped database facts and persist generated reports."""

    def __init__(self, database_session: Session) -> None:
        """Store the database session used by report operations."""

        self.database_session = database_session

    def generate(
        self,
        report_type: str,
        period: str,
        department_id: int | None,
        created_by: int | None,
    ) -> Report:
        """Generate and persist a report from structured database data."""

        data = self._collect_data(period, department_id)
        result = ReportGenerator().generate(data)

        report = Report(
            report_type=report_type,
            period=period,
            department_id=department_id,
            content=result["content"],
            summary_json={**data, "_source": result["_source"]},
            created_by=created_by,
        )
        self.database_session.add(report)
        self.database_session.commit()
        self.database_session.refresh(report)
        return report

    def update_content(self, report: Report, content: str) -> Report:
        """Cập nhật toàn bộ Markdown của báo cáo (tính năng Edit — sửa trực tiếp Markdown)."""
        report.content = content
        self.database_session.commit()
        self.database_session.refresh(report)
        return report

    def delete(self, report: Report) -> None:
        """Delete a persisted report."""

        self.database_session.delete(report)
        self.database_session.commit()

    def _collect_data(self, period: str, department_id: int | None) -> dict:
        """Collect task, KPI, risk, and personnel facts for report generation."""

        task_query = self.database_session.query(Task)
        user_query = self.database_session.query(User).filter(User.role != "admin")
        if department_id:
            task_query = task_query.filter(Task.department_id == department_id)
            user_query = user_query.filter(User.department_id == department_id)

        task_status_query = self.database_session.query(
            Task.status, func.count(Task.id)
        )
        if department_id:
            task_status_query = task_status_query.filter(
                Task.department_id == department_id
            )
        tasks_by_status = dict(task_status_query.group_by(Task.status).all())

        risk_users = (
            self.database_session.query(
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
            .order_by(KPIScore.total_score.asc())
        )
        if department_id:
            risk_users = risk_users.filter(User.department_id == department_id)
        risk_user_rows = risk_users.limit(10).all()

        # Dữ liệu chi tiết nhiệm vụ chậm/chưa hoàn thành — BẮT BUỘC để LLM điền bảng HTML
        # theo report_generator_prompt.txt (mục "3. Nhiệm vụ chậm" yêu cầu bảng chi tiết
        # with task, unit, assignee, status, and deadline columns.
        slow_task_query = (
            self.database_session.query(Task, Department.name, TaskAssignment.user_id)
            .outerjoin(Department, Department.id == Task.department_id)
            .outerjoin(TaskAssignment, TaskAssignment.task_id == Task.id)
            .filter(Task.status.in_(["OVERDUE", "IN_PROGRESS", "NOT_STARTED"]))
        )
        if department_id:
            slow_task_query = slow_task_query.filter(
                Task.department_id == department_id
            )
        slow_task_rows = (
            slow_task_query.order_by(Task.deadline.asc().nullslast()).limit(30).all()
        )
        user_name_by_id = {
            user_id: full_name
            for user_id, full_name in self.database_session.query(
                User.id, User.full_name
            ).all()
        }
        slow_tasks = []
        for task, dept_name, assignee_user_id in slow_task_rows:
            slow_tasks.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "department": dept_name,
                    "assignee": user_name_by_id.get(
                        assignee_user_id, "(chưa phân công)"
                    ),
                    "status": task.status,
                    "deadline": task.deadline.strftime("%d/%m/%Y")
                    if task.deadline
                    else None,
                }
            )

        average_kpi_query = self.database_session.query(
            func.avg(KPIScore.total_score)
        ).filter(KPIScore.period_month == period)
        if department_id:
            average_kpi_query = average_kpi_query.join(
                User, User.id == KPIScore.user_id
            ).filter(User.department_id == department_id)
        average_kpi = average_kpi_query.scalar()

        return {
            "period": period,
            "department_id": department_id,
            "total_users": user_query.count(),
            "total_tasks": task_query.count(),
            "tasks_by_status": tasks_by_status,
            "avg_kpi": round(float(average_kpi), 1)
            if average_kpi is not None
            else None,
            "slow_tasks": slow_tasks,
            "risk_users": [
                {
                    "name": risk_user[0],
                    "department": risk_user[1],
                    "score": risk_user[2],
                    "risk": risk_user[3],
                }
                for risk_user in risk_user_rows
            ],
        }
