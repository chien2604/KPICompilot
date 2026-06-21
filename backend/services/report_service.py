from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_layer.report_generator import ReportGenerator
from db.models.departments import Department
from db.models.kpi import KPIScore
from db.models.reports import Report
from db.models.tasks import Task, TaskAssignment
from db.models.users import User


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def generate(self, report_type: str, period: str, department_id: int | None, created_by: int | None) -> Report:
        data = self._collect_data(period, department_id)
        result = ReportGenerator().generate(data)

        report = Report(
            report_type=report_type,
            period=period,
            department_id=department_id,
            content=result["html"],
            summary_json={**data, "_source": result["_source"]},
            created_by=created_by,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def update_content(self, report: Report, content: str) -> Report:
        """Cập nhật toàn bộ HTML của báo cáo (tính năng Edit — sửa trực tiếp HTML)."""
        report.content = content
        self.db.commit()
        self.db.refresh(report)
        return report

    def delete(self, report: Report) -> None:
        self.db.delete(report)
        self.db.commit()

    def render_pdf_html(self, report: Report) -> str:
        """Bọc content (HTML fragment) trong 1 trang HTML đầy đủ kèm CSS in ấn, để gửi sang PDF render service."""
        return self._wrap_print_document(report.content)

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

        # Dữ liệu chi tiết nhiệm vụ chậm/chưa hoàn thành — BẮT BUỘC để LLM điền bảng HTML
        # theo report_generator_prompt.txt (mục "3. Nhiệm vụ chậm" yêu cầu bảng chi tiết
        # với cột Nhiệm vụ, Phòng ban, Người phụ trách, Trạng thái, Hạn xử lý).
        slow_task_query = (
            self.db.query(Task, Department.name, TaskAssignment.user_id)
            .outerjoin(Department, Department.id == Task.department_id)
            .outerjoin(TaskAssignment, TaskAssignment.task_id == Task.id)
            .filter(Task.status.in_(["OVERDUE", "IN_PROGRESS", "NOT_STARTED"]))
        )
        if department_id:
            slow_task_query = slow_task_query.filter(Task.department_id == department_id)
        slow_task_rows = slow_task_query.order_by(Task.deadline.asc().nullslast()).limit(30).all()
        user_name_by_id = {u.id: u.full_name for u in self.db.query(User.id, User.full_name).all()}
        slow_tasks = []
        for task, dept_name, assignee_user_id in slow_task_rows:
            slow_tasks.append({
                "task_id": task.id,
                "title": task.title,
                "department": dept_name,
                "assignee": user_name_by_id.get(assignee_user_id, "(chưa phân công)"),
                "status": task.status,
                "deadline": task.deadline.strftime("%d/%m/%Y") if task.deadline else None,
            })

        avg_kpi = self.db.query(func.avg(KPIScore.total_score)).filter(KPIScore.period_month == period).scalar()

        return {
            "period": period,
            "department_id": department_id,
            "total_users": user_query.count(),
            "total_tasks": task_query.count(),
            "tasks_by_status": tasks_by_status,
            "avg_kpi": round(float(avg_kpi), 1) if avg_kpi is not None else None,
            "slow_tasks": slow_tasks,
            "risk_users": [{"name": r[0], "department": r[1], "score": r[2], "risk": r[3]} for r in risk_users],
        }

    @staticmethod
    def _wrap_print_document(content_html: str) -> str:
        css = """
        body { font-family: 'Times New Roman', serif; color: #111; margin: 0; padding: 28mm 22mm; font-size: 13px; line-height: 1.6; }
        h2 { font-size: 16px; margin: 12px 0; }
        h3 { font-size: 14px; margin: 16px 0 8px; }
        p { margin: 6px 0; }
        table { width: 100%; border-collapse: collapse; margin: 8px 0 16px; font-size: 12.5px; }
        table th, table td { border: 1px solid #444; padding: 6px 8px; text-align: left; }
        table th { background: #f1f1f1; }
        ul, ol { padding-left: 22px; }
        """
        return f"<!doctype html><html lang='vi'><head><meta charset='utf-8'/><style>{css}</style></head><body>{content_html}</body></html>"