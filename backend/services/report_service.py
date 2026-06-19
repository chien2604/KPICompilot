from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_layer.report_generator import ReportGenerator
from db.models.departments import Department
from db.models.kpi import KPIScore
from db.models.reports import Report
from db.models.tasks import Task
from db.models.users import User


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def generate(self, report_type: str, period: str, department_id: int | None, created_by: int | None) -> Report:
        data = self._collect_data(period, department_id)
        content = ReportGenerator().generate(data)
        report = Report(
            report_type=report_type,
            period=period,
            department_id=department_id,
            content=content,
            summary_json=data,
            created_by=created_by,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def _collect_data(self, period: str, department_id: int | None) -> dict:
        task_query = self.db.query(Task)
        user_query = self.db.query(User)
        if department_id:
            task_query = task_query.filter(Task.department_id == department_id)
            user_query = user_query.filter(User.department_id == department_id)
        tasks_by_status = dict(self.db.query(Task.status, func.count(Task.id)).group_by(Task.status).all())
        risk_users = (
            self.db.query(User.full_name, Department.name, KPIScore.total_score, KPIScore.risk_level)
            .join(KPIScore, KPIScore.user_id == User.id)
            .outerjoin(Department, Department.id == User.department_id)
            .filter(KPIScore.period_month == period, KPIScore.risk_level.in_(["HIGH", "MEDIUM"]))
            .order_by(KPIScore.total_score.asc())
            .limit(10)
            .all()
        )
        return {
            "period": period,
            "department_id": department_id,
            "total_users": user_query.count(),
            "total_tasks": task_query.count(),
            "tasks_by_status": tasks_by_status,
            "risk_users": [{"name": r[0], "department": r[1], "score": r[2], "risk": r[3]} for r in risk_users],
        }
