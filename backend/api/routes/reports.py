import markdown
from ai_layer.report_docx_renderer import render_report_docx
from core.deps import get_current_user
from core.organization import LEADERSHIP_ROLE, UNIT_DEPUTY_ROLE, UNIT_HEAD_ROLE
from core.permissions import is_admin
from db.database import get_db
from db.models.reports import Report
from db.models.users import User
from fastapi import APIRouter, Depends, HTTPException, Response
from schemas.reports import ReportContentUpdateIn, ReportGenerateIn
from services.report_service import ReportService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/reports", tags=["reports"])


def report_to_dict(report: Report) -> dict:
    """Serialize a report and render its Markdown preview."""

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
    """Return a report after applying organization or unit access rules."""

    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo")

    can_view_reports = current_user.organization_role in {
        LEADERSHIP_ROLE,
        UNIT_HEAD_ROLE,
        UNIT_DEPUTY_ROLE,
    }
    if not is_admin(current_user) and not can_view_reports:
        raise HTTPException(
            status_code=403, detail="Thành viên không có quyền xem báo cáo."
        )
    if (
        not is_admin(current_user)
        and current_user.organization_role != LEADERSHIP_ROLE
        and report.department_id != current_user.department_id
    ):
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền xem báo cáo của đơn vị khác."
        )

    return report


@router.post("/generate")
def generate_report(
    payload: ReportGenerateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate a report within the current leader's permitted scope."""

    can_generate_reports = current_user.organization_role in {
        LEADERSHIP_ROLE,
        UNIT_HEAD_ROLE,
        UNIT_DEPUTY_ROLE,
    }
    if not is_admin(current_user) and not can_generate_reports:
        raise HTTPException(
            status_code=403, detail="Thành viên không có quyền tạo báo cáo."
        )
    if (
        not is_admin(current_user)
        and current_user.organization_role != LEADERSHIP_ROLE
    ):
        payload.department_id = current_user.department_id

    # Override created_by for security
    return report_to_dict(
        ReportService(db).generate(
            payload.report_type, payload.period, payload.department_id, current_user.id
        )
    )


@router.get("")
def list_reports(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[dict]:
    """List reports visible to organization and unit managers."""

    can_view_reports = current_user.organization_role in {
        LEADERSHIP_ROLE,
        UNIT_HEAD_ROLE,
        UNIT_DEPUTY_ROLE,
    }
    if not is_admin(current_user) and not can_view_reports:
        raise HTTPException(
            status_code=403, detail="Thành viên không có quyền xem báo cáo."
        )

    query = db.query(Report)
    if (
        not is_admin(current_user)
        and current_user.organization_role != LEADERSHIP_ROLE
    ):
        query = query.filter(Report.department_id == current_user.department_id)

    return [
        report_to_dict(item) for item in query.order_by(Report.created_at.desc()).all()
    ]


@router.get("/{report_id}")
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return one report in the current user's scope."""

    return report_to_dict(_get_report_or_404(report_id, db, current_user))


@router.patch("/{report_id}")
def update_report(
    report_id: int,
    payload: ReportContentUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Sửa nội dung báo cáo (tính năng Edit) — nhận toàn bộ Markdown mới."""
    report = _get_report_or_404(report_id, db, current_user)
    updated = ReportService(db).update_content(report, payload.content)
    return report_to_dict(updated)


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a report in the current user's scope."""

    report = _get_report_or_404(report_id, db, current_user)
    ReportService(db).delete(report)
    return {"ok": True}


@router.get("/{report_id}/export/docx")
def export_report_docx(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Export a permitted report as a DOCX attachment."""

    report = _get_report_or_404(report_id, db, current_user)
    docx_bytes = render_report_docx(report.content)
    filename = f"bao-cao-{report.period}-{report.id}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
