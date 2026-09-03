import json

from core.deps import get_current_user
from core.organization import UBND_AUTHORITY_ROLE, UNIT_DEPUTY_ROLE, UNIT_HEAD_ROLE
from core.permissions import (
    can_verify_task_result,
    can_view_user,
    get_visible_users,
    is_admin,
)
from db.database import get_db
from db.models.evidences import TaskEvidence
from db.models.tasks import Task, TaskAssignment
from db.models.users import User
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from schemas.evidences import EvidenceReferenceCreate, EvidenceVerificationUpdate
from services.audit_service import record_audit_event
from services.evidence_service import EvidenceService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/evidences", tags=["evidences"])


def evidence_to_dict(item: TaskEvidence) -> dict:
    """Serialize an evidence row for API responses."""

    return {
        "id": item.id,
        "task_id": item.task_id,
        "assignment_id": item.assignment_id,
        "uploaded_by": item.uploaded_by,
        "file_name": item.file_name,
        "file_type": item.file_type,
        "file_path": item.file_path,
        "extracted_text": item.extracted_text,
        "ai_relevance_score": item.ai_relevance_score,
        "ai_summary": item.ai_summary,
        "ai_missing_points": item.ai_missing_points,
        "status": item.status,
        "result_type": item.result_type,
        "source_type": item.source_type,
        "source_system": item.source_system,
        "source_record_id": item.source_record_id,
        "document_number": item.document_number,
        "metadata": item.metadata_json,
        "file_hash_sha256": item.file_hash_sha256,
        "verification_status": item.verification_status,
        "verified_by": item.verified_by,
        "verified_at": item.verified_at,
        "verification_note": item.verification_note,
        "created_at": item.created_at,
    }


@router.post("/upload")
def upload_evidence(
    task_id: int = Form(...),
    assignment_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload and process evidence for an assigned task."""

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ")

    assignment = db.get(TaskAssignment, assignment_id)
    if assignment is None or assignment.task_id != task_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy phân công nhiệm vụ.")
    if assignment.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Chỉ người thực hiện mới được tải lên minh chứng"
        )

    return evidence_to_dict(
        EvidenceService(db).upload_and_process(task_id, assignment_id, current_user.id, file)
    )


@router.post("/reference")
def create_evidence_reference(
    payload: EvidenceReferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Submit a link to a product stored in another authorized system."""

    assignment = db.get(TaskAssignment, payload.assignment_id)
    if assignment is None or assignment.task_id != payload.task_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy phân công nhiệm vụ.")
    if assignment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Chỉ người thực hiện được nộp sản phẩm.")
    return evidence_to_dict(EvidenceService(db).create_reference(
        task_id=payload.task_id,
        assignment_id=payload.assignment_id,
        uploaded_by=current_user.id,
        payload=payload,
    ))


@router.get("")
def list_evidences(
    uploaded_by: int | None = None,
    task_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List evidence within organization, unit, or uploader scope."""

    query = db.query(TaskEvidence)
    if current_user.organization_role == UBND_AUTHORITY_ROLE or is_admin(current_user):
        pass
    elif current_user.organization_role in {UNIT_HEAD_ROLE, UNIT_DEPUTY_ROLE}:
        visible_user_ids = [
            user.id
            for user in get_visible_users(
                current_user,
                db.query(User).all(),
            )
        ]
        query = query.filter(TaskEvidence.uploaded_by.in_(visible_user_ids))
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


def check_evidence_permission(
    evidence: TaskEvidence,
    current_user: User,
    database_session: Session,
) -> None:
    """Raise a forbidden response when evidence is outside the user's scope."""

    if is_admin(current_user):
        return
    if current_user.organization_role == UBND_AUTHORITY_ROLE:
        return
    if current_user.organization_role == UNIT_HEAD_ROLE:
        if evidence.task.department_id == current_user.department_id:
            return
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem minh chứng của đơn vị khác.",
        )
    uploader = database_session.get(User, evidence.uploaded_by)
    if uploader is None or not can_view_user(current_user, uploader):
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền xem minh chứng này"
        )


@router.patch("/{evidence_id}/verify")
def verify_evidence(
    evidence_id: int,
    payload: EvidenceVerificationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Record a human approval or rejection; AI analysis cannot call this action."""

    item = db.get(TaskEvidence, evidence_id)
    if item is None or item.assignment_id is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm hợp lệ.")
    assignment = db.get(TaskAssignment, item.assignment_id)
    target = db.get(User, assignment.user_id) if assignment else None
    if target is None or not can_verify_task_result(current_user, target):
        raise HTTPException(status_code=403, detail="Không có thẩm quyền xác minh sản phẩm này.")
    if payload.verification_status not in {"VERIFIED", "REJECTED"}:
        raise HTTPException(status_code=400, detail="Trạng thái phải là VERIFIED hoặc REJECTED.")
    from datetime import datetime

    before = {"verification_status": item.verification_status}
    item.verification_status = payload.verification_status
    item.verified_by = current_user.id
    item.verified_at = datetime.utcnow()
    item.verification_note = payload.note
    record_audit_event(
        db,
        actor_id=current_user.id,
        action="EVIDENCE_VERIFIED",
        entity_type="TASK_EVIDENCE",
        entity_id=item.id,
        before=before,
        after={"verification_status": item.verification_status},
        reason=payload.note,
    )
    db.commit()
    db.refresh(item)
    return evidence_to_dict(item)


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
    check_evidence_permission(item, current_user, db)

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

    check_evidence_permission(item, current_user, db)

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
    check_evidence_permission(item, current_user, db)
    return evidence_to_dict(item)
