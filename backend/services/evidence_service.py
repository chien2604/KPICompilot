import hashlib
import json
import logging
from pathlib import Path

from ai_layer.evidence_analyzer import EvidenceAnalyzer
from ai_layer.rag.graph_rag_service import GraphRAGService
from db.models.evidences import TaskEvidence
from db.models.tasks import Task
from db.models.users import User
from fastapi import UploadFile
from sqlalchemy.orm import Session

from services.audit_service import record_audit_event
from services.file_storage import FileStorage

logger = logging.getLogger(__name__)


class EvidenceService:
    """Persist task outputs and keep AI analysis advisory."""

    def __init__(self, db: Session) -> None:
        """Initialize the evidence service."""

        self.db = db
        self.storage = FileStorage()

    def upload_and_process(
        self, task_id: int, assignment_id: int, uploaded_by: int, file: UploadFile
    ) -> TaskEvidence:
        """Store a file output, then attempt advisory AI analysis."""

        file_name, file_path = self.storage.save_upload(file)
        evidence = TaskEvidence(
            task_id=task_id,
            assignment_id=assignment_id,
            uploaded_by=uploaded_by,
            file_name=file_name,
            file_type=file.content_type,
            file_path=file_path,
            status="PROCESSING",
            verification_status="PENDING_REVIEW",
        )
        evidence.file_hash_sha256 = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
        self.db.add(evidence)
        self.db.flush()
        try:
            rag = GraphRAGService(self.db)
            indexed = rag.index_evidence(evidence.id)
            task = self.db.get(Task, task_id)
            user = self.db.get(User, uploaded_by)
            uploader_name = user.full_name if user else "(không rõ)"
            department_name = (
                user.department.name if user and user.department else "(không rõ)"
            )
            task_deadline = (
                task.deadline.strftime("%d/%m/%Y")
                if task and task.deadline
                else "(chưa đặt)"
            )

            analysis = EvidenceAnalyzer().analyze(
                task_title=task.title if task else "",
                task_description=task.description if task else "",
                evidence_text=indexed["text"],
                uploader_name=uploader_name,
                department=department_name,
                task_deadline=task_deadline,
                filename=file_name,
                file_type=file.content_type,
            )
            evidence.ai_relevance_score = float(analysis.get("relevance_score") or 0)
            evidence.ai_summary = analysis.get("summary")
            evidence.ai_missing_points = json.dumps(
                {
                    "checklist": analysis.get("checklist", []),
                    "strengths": analysis.get("strengths", []),
                    "weaknesses": analysis.get("weaknesses", []),
                },
                ensure_ascii=False,
            )
            evidence.status = "ANALYZED"
            evidence.ai_analysis_json = analysis
            record_audit_event(
                self.db,
                actor_id=uploaded_by,
                action="PRODUCT_SUBMITTED",
                entity_type="TASK_EVIDENCE",
                entity_id=evidence.id,
                after={"source_type": evidence.source_type, "assignment_id": assignment_id},
            )
        except Exception as exc:
            logger.exception("Không thể phân tích sản phẩm %s bằng AI", file_name)
            self.db.rollback()
            new_evidence = TaskEvidence(
                task_id=task_id,
                assignment_id=assignment_id,
                uploaded_by=uploaded_by,
                file_name=file_name,
                file_type=file.content_type,
                file_path=file_path,
                file_hash_sha256=evidence.file_hash_sha256,
                status="AI_CHECK_FAILED",
                verification_status="PENDING_REVIEW",
                ai_summary=(
                    "AI chưa thể phân tích sản phẩm. "
                    "Người có thẩm quyền vẫn có thể kiểm tra và xác minh."
                ),
            )
            self.db.add(new_evidence)
            self.db.flush()
            record_audit_event(
                self.db,
                actor_id=uploaded_by,
                action="PRODUCT_SUBMITTED",
                entity_type="TASK_EVIDENCE",
                entity_id=new_evidence.id,
                after={
                    "source_type": new_evidence.source_type,
                    "assignment_id": assignment_id,
                    "ai_status": "FAILED",
                    "error_type": type(exc).__name__,
                },
            )
            self.db.commit()
            self.db.refresh(new_evidence)
            return new_evidence

        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def create_reference(
        self, *, task_id: int, assignment_id: int, uploaded_by: int, payload
    ) -> TaskEvidence:
        """Create a linked output without downloading or duplicating the source file."""

        evidence = TaskEvidence(
            task_id=task_id,
            assignment_id=assignment_id,
            uploaded_by=uploaded_by,
            result_type=payload.result_type,
            source_type="EXTERNAL_LINK",
            source_system=payload.source_system,
            source_record_id=payload.source_record_id,
            document_number=payload.document_number,
            metadata_json=payload.metadata,
            file_name=payload.title,
            file_type="text/uri-list",
            file_path=str(payload.url),
            status="UPLOADED",
            verification_status="PENDING_REVIEW",
        )
        self.db.add(evidence)
        self.db.flush()
        record_audit_event(
            self.db,
            actor_id=uploaded_by,
            action="PRODUCT_SUBMITTED",
            entity_type="TASK_EVIDENCE",
            entity_id=evidence.id,
            after={"source_type": evidence.source_type, "assignment_id": assignment_id},
        )
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def analyze(self, evidence_id: int) -> TaskEvidence:
        """Run advisory content analysis without changing human verification."""

        evidence = self.db.get(TaskEvidence, evidence_id)
        if not evidence:
            raise ValueError("Không tìm thấy minh chứng")
        task = self.db.get(Task, evidence.task_id)
        user = self.db.get(User, evidence.uploaded_by)
        uploader_name = user.full_name if user else "(không rõ)"
        department_name = (
            user.department.name if user and user.department else "(không rõ)"
        )
        task_deadline = (
            task.deadline.strftime("%d/%m/%Y")
            if task and task.deadline
            else "(chưa đặt)"
        )

        analysis = EvidenceAnalyzer().analyze(
            task_title=task.title if task else "",
            task_description=task.description if task else "",
            evidence_text=evidence.extracted_text or "",
            uploader_name=uploader_name,
            department=department_name,
            task_deadline=task_deadline,
            filename=evidence.file_name,
            file_type=evidence.file_type,
        )
        evidence.ai_relevance_score = float(analysis.get("relevance_score") or 0)
        evidence.ai_summary = analysis.get("summary")
        evidence.ai_missing_points = json.dumps(
            {
                "checklist": analysis.get("checklist", []),
                "strengths": analysis.get("strengths", []),
                "weaknesses": analysis.get("weaknesses", []),
            },
            ensure_ascii=False,
        )
        evidence.status = "ANALYZED"
        self.db.commit()
        self.db.refresh(evidence)
        return evidence
