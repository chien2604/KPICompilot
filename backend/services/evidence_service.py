import json

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ai_layer.evidence_analyzer import EvidenceAnalyzer
from ai_layer.rag.graph_rag_service import GraphRAGService
from db.models.evidences import TaskEvidence
from db.models.tasks import Task
from services.file_storage import FileStorage


class EvidenceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.storage = FileStorage()

    def upload_and_process(self, task_id: int, uploaded_by: int, file: UploadFile) -> TaskEvidence:
        file_name, file_path = self.storage.save_upload(file)
        evidence = TaskEvidence(
            task_id=task_id,
            uploaded_by=uploaded_by,
            file_name=file_name,
            file_type=file.content_type,
            file_path=file_path,
            status="PROCESSING",
        )
        self.db.add(evidence)
        self.db.flush()
        try:
            rag = GraphRAGService(self.db)
            indexed = rag.index_evidence(evidence.id)
            task = self.db.get(Task, task_id)
            analysis = EvidenceAnalyzer().analyze(task.title if task else "", task.description if task else "", indexed["text"])
            evidence.ai_relevance_score = float(analysis.get("relevance_score") or 0)
            evidence.ai_summary = analysis.get("summary")
            evidence.ai_missing_points = json.dumps(analysis.get("missing_points", []), ensure_ascii=False)
            evidence.status = "ANALYZED"
        except Exception as exc:
            evidence.status = "FAILED"
            evidence.ai_summary = f"Lỗi xử lý minh chứng: {exc}"
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def analyze(self, evidence_id: int) -> TaskEvidence:
        evidence = self.db.get(TaskEvidence, evidence_id)
        if not evidence:
            raise ValueError("Không tìm thấy minh chứng")
        task = self.db.get(Task, evidence.task_id)
        analysis = EvidenceAnalyzer().analyze(task.title if task else "", task.description if task else "", evidence.extracted_text or "")
        evidence.ai_relevance_score = float(analysis.get("relevance_score") or 0)
        evidence.ai_summary = analysis.get("summary")
        evidence.ai_missing_points = json.dumps(analysis.get("missing_points", []), ensure_ascii=False)
        evidence.status = "ANALYZED"
        self.db.commit()
        self.db.refresh(evidence)
        return evidence
