from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ai_layer.report_docx_renderer import render_report_docx
from db.database import get_db
from db.models.reports import Report
from db.models.users import User
from core.deps import get_current_user
from core.permissions import get_user_level
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


def _get_report_or_404(report_id: int, db: Session, current_user: User) -> Report:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo")
    
    level = get_user_level(current_user)
    if level == 5:
        raise HTTPException(status_code=403, detail="Chuyên viên không có quyền xem báo cáo")
    if level in [3, 4] and report.department_id and report.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem báo cáo của phòng khác")
        
    return report


@router.post("/generate")
def generate_report(payload: ReportGenerateIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    level = get_user_level(current_user)
    if level == 5:
        raise HTTPException(status_code=403, detail="Chuyên viên không có quyền tạo báo cáo")
    if level in [3, 4] and payload.department_id and payload.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền tạo báo cáo cho phòng khác")
    
    # Override created_by for security
    return report_to_dict(ReportService(db).generate(payload.report_type, payload.period, payload.department_id, current_user.id))


@router.get("")
def list_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    level = get_user_level(current_user)
    if level == 5:
        raise HTTPException(status_code=403, detail="Chuyên viên không có quyền xem báo cáo")
        
    query = db.query(Report)
    if level in [3, 4]:
        query = query.filter(Report.department_id == current_user.department_id)
        
    return [report_to_dict(item) for item in query.order_by(Report.created_at.desc()).all()]


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return report_to_dict(_get_report_or_404(report_id, db, current_user))


@router.patch("/{report_id}")
def update_report(report_id: int, payload: ReportContentUpdateIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    """Sửa nội dung báo cáo (tính năng Edit) — nhận toàn bộ Markdown mới."""
    report = _get_report_or_404(report_id, db, current_user)
    updated = ReportService(db).update_content(report, payload.content)
    return report_to_dict(updated)


@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    report = _get_report_or_404(report_id, db, current_user)
    ReportService(db).delete(report)
    return {"ok": True}


@router.get("/{report_id}/export/docx")
def export_report_docx(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    report = _get_report_or_404(report_id, db, current_user)
    docx_bytes = render_report_docx(report.content)
    filename = f"bao-cao-{report.period}-{report.id}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )