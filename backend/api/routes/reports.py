from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.reports import Report
from schemas.reports import ReportGenerateIn
from services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def report_to_dict(report: Report) -> dict:
    return {
        "id": report.id,
        "report_type": report.report_type,
        "period": report.period,
        "department_id": report.department_id,
        "content": report.content,
        "summary_json": report.summary_json,
        "created_by": report.created_by,
        "created_at": report.created_at,
    }


@router.post("/generate")
def generate_report(payload: ReportGenerateIn, db: Session = Depends(get_db)) -> dict:
    return report_to_dict(ReportService(db).generate(payload.report_type, payload.period, payload.department_id, payload.created_by))


@router.get("")
def list_reports(db: Session = Depends(get_db)) -> list[dict]:
    return [report_to_dict(item) for item in db.query(Report).order_by(Report.created_at.desc()).all()]


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)) -> dict:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo")
    return report_to_dict(report)
