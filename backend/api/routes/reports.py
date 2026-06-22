from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ai_layer.report_docx_renderer import render_report_docx
from db.database import get_db
from db.models.reports import Report
from schemas.reports import ReportContentUpdateIn, ReportGenerateIn
from services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def report_to_dict(report: Report) -> dict:
    import markdown
    content_html = markdown.markdown(report.content or "", extensions=["tables"])
    return {
        "id": report.id,
        "report_type": report.report_type,
        "period": report.period,
        "department_id": report.department_id,
        "content": report.content,
        "content_html": content_html,
        "summary_json": report.summary_json,
        "created_by": report.created_by,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


def _get_report_or_404(report_id: int, db: Session) -> Report:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo")
    return report


@router.post("/generate")
def generate_report(payload: ReportGenerateIn, db: Session = Depends(get_db)) -> dict:
    return report_to_dict(ReportService(db).generate(payload.report_type, payload.period, payload.department_id, payload.created_by))


@router.get("")
def list_reports(db: Session = Depends(get_db)) -> list[dict]:
    return [report_to_dict(item) for item in db.query(Report).order_by(Report.created_at.desc()).all()]


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)) -> dict:
    return report_to_dict(_get_report_or_404(report_id, db))


@router.patch("/{report_id}")
def update_report(report_id: int, payload: ReportContentUpdateIn, db: Session = Depends(get_db)) -> dict:
    """Sửa nội dung báo cáo (tính năng Edit) — nhận toàn bộ Markdown mới."""
    report = _get_report_or_404(report_id, db)
    updated = ReportService(db).update_content(report, payload.content)
    return report_to_dict(updated)


@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)) -> dict:
    report = _get_report_or_404(report_id, db)
    ReportService(db).delete(report)
    return {"ok": True}


@router.get("/{report_id}/export/docx")
def export_report_docx(report_id: int, db: Session = Depends(get_db)) -> Response:
    report = _get_report_or_404(report_id, db)
    docx_bytes = render_report_docx(report.content)
    filename = f"bao-cao-{report.period}-{report.id}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )