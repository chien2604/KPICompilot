import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.evidences import TaskEvidence
from services.evidence_service import EvidenceService

router = APIRouter(prefix="/evidences", tags=["evidences"])


def evidence_to_dict(item: TaskEvidence) -> dict:
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
def upload_evidence(task_id: int = Form(...), uploaded_by: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    return evidence_to_dict(EvidenceService(db).upload_and_process(task_id, uploaded_by, file))


@router.get("")
def list_evidences(uploaded_by: int | None = None, task_id: int | None = None, db: Session = Depends(get_db)) -> list[dict]:
    query = db.query(TaskEvidence)
    if uploaded_by is not None:
        query = query.filter(TaskEvidence.uploaded_by == uploaded_by)
    if task_id is not None:
        query = query.filter(TaskEvidence.task_id == task_id)
    return [evidence_to_dict(item) for item in query.order_by(TaskEvidence.created_at.desc()).all()]


@router.post("/{evidence_id}/analyze")
def analyze_evidence(evidence_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        item = EvidenceService(db).analyze(evidence_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return evidence_to_dict(item)


@router.get("/{evidence_id}/analysis")
def get_analysis(evidence_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(TaskEvidence, evidence_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy minh chứng")
    
    missing_data = {}
    if item.ai_missing_points:
        try:
            parsed = json.loads(item.ai_missing_points)
            if isinstance(parsed, dict):
                missing_data = parsed
            elif isinstance(parsed, list):
                missing_data = {"checklist": parsed, "strengths": [], "weaknesses": []}
        except Exception:
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
def get_evidence(evidence_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(TaskEvidence, evidence_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy minh chứng")
    return evidence_to_dict(item)
