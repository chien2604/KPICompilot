import json

from core.deps import get_current_user
from core.organization import LEADERSHIP_ROLE, UNIT_DEPUTY_ROLE, UNIT_HEAD_ROLE
from core.permissions import is_admin
from db.database import get_db
from db.models.evidences import TaskEvidence
from db.models.tasks import Task
from db.models.users import User
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from services.evidence_service import EvidenceService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/evidences", tags=["evidences"])


def evidence_to_dict(item: TaskEvidence) -> dict:
    """Serialize an evidence row for API responses."""

    return {
        "id": item.id,
        "task_id": item.task_id,
        "uploaded_by": item.uploaded_by,
        "file_name": item.file_name,
        "file_type": item.file_type,
        "file_path": item.file_path,
        "extracted_text": item.extracted_text,
        "ai_relevance_score": item.ai_relevance_score,
        "ai_summary": item.ai_summary,
        "ai_missing_points": item.ai_missing_points,
        "status": item.status,
        "created_at": item.created_at,
    }


@router.post("/upload")
def upload_evidence(
    task_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload and process evidence for an assigned task."""

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")

    # Người thực hiện, người quản lý đúng phạm vi hoặc quản trị viên được tải minh chứng.
    is_assignee = current_user.id in [a.user_id for a in task.assignments]
    has_organization_scope = current_user.organization_role == LEADERSHIP_ROLE
    has_unit_scope = (
        current_user.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}
        and task.department_id == current_user.department_id
    )
    if not any(
        [is_admin(current_user), is_assignee, has_organization_scope, has_unit_scope]
    ):
        raise HTTPException(
            status_code=403, detail="Chỉ người thực hiện mới được tải lên minh chứng"
        )

    return evidence_to_dict(
        EvidenceService(db).upload_and_process(task_id, current_user.id, file)
    )


@router.get("")
def list_evidences(
    uploaded_by: int | None = None,
    task_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List evidence within organization, unit, or uploader scope."""

    query = db.query(TaskEvidence)
    if current_user.organization_role == LEADERSHIP_ROLE or is_admin(current_user):
        pass
    elif current_user.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}:
        query = query.join(Task).filter(
            Task.department_id == current_user.department_id
        )
    else:
        query = query.filter(TaskEvidence.uploaded_by == current_user.id)

    if uploaded_by is not None:
        query = query.filter(TaskEvidence.uploaded_by == uploaded_by)
    if task_id is not None:
        query = query.filter(TaskEvidence.task_id == task_id)
    return [
        evidence_to_dict(item)
        for item in query.order_by(TaskEvidence.created_at.desc()).all()
    ]


def check_evidence_permission(evidence: TaskEvidence, current_user: User) -> None:
    """Raise a forbidden response when evidence is outside the user's scope."""

    if is_admin(current_user):
        return
    if current_user.organization_role == LEADERSHIP_ROLE:
        return
    if current_user.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}:
        if evidence.task.department_id == current_user.department_id:
            return
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem minh chứng của đơn vị khác.",
        )
    if evidence.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền xem minh chứng này"
        )


@router.post("/{evidence_id}/analyze")
def analyze_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Run AI analysis again for an allowed evidence item."""

    item = db.get(TaskEvidence, evidence_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy minh chứng")
    check_evidence_permission(item, current_user)

    try:
        item = EvidenceService(db).analyze(evidence_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return evidence_to_dict(item)


@router.get("/{evidence_id}/analysis")
def get_analysis(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return structured AI analysis for an evidence item."""

    item = db.get(TaskEvidence, evidence_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy minh chứng")

    check_evidence_permission(item, current_user)

    missing_data = {}
    if item.ai_missing_points:
        try:
            parsed = json.loads(item.ai_missing_points)
            if isinstance(parsed, dict):
                missing_data = parsed
            elif isinstance(parsed, list):
                missing_data = {"checklist": parsed, "strengths": [], "weaknesses": []}
        except json.JSONDecodeError:
            missing_data = {"checklist": [], "strengths": [], "weaknesses": []}

    return {
        "evidence_id": item.id,
        "task_id": item.task_id,
        "relevance_score": item.ai_relevance_score,
        "summary": item.ai_summary,
        "checklist": missing_data.get("checklist", []),
        "strengths": missing_data.get("strengths", []),
        "weaknesses": missing_data.get("weaknesses", []),
        "status": item.status,
        "extracted_text": item.extracted_text,
    }


@router.get("/{evidence_id}")
def get_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return one evidence item within the current user's scope."""

    item = db.get(TaskEvidence, evidence_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy minh chứng")
    check_evidence_permission(item, current_user)
    return evidence_to_dict(item)
