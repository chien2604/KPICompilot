from sqlalchemy.orm import Session

from ai_layer.rag.chunker import TextChunker
from ai_layer.rag.document_loader import DocumentLoader
from ai_layer.rag.embedding_client import get_embedding_client
from ai_layer.rag.kuzu_graph_store import KuzuGraphStore
from ai_layer.rag.pgvector_store import PGVectorStore
from core.config import get_settings
from db.models.evidences import TaskEvidence
from db.models.tasks import Task, TaskAssignment


class GraphRAGService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.loader = DocumentLoader()
        self.chunker = TextChunker()
        self.embedding = get_embedding_client()
        self.vector_store = PGVectorStore(db, self.embedding)
        self.graph = KuzuGraphStore(str(get_settings().kuzu_db_path))
        self.graph.init_schema()

    def index_evidence(self, evidence_id: int) -> dict:
        evidence = self.db.get(TaskEvidence, evidence_id)
        if not evidence:
            raise ValueError("Không tìm thấy minh chứng")
        task = self.db.get(Task, evidence.task_id)
        text = self.loader.extract_text(evidence.file_path)
        chunks = self.chunker.split(text)
        embeddings = self.embedding.embed_texts(chunks)
        rows = self.vector_store.add_chunks(evidence.id, evidence.task_id, chunks, embeddings)
        evidence.extracted_text = text
        self._sync_graph(evidence, task, rows)
        self.db.flush()
        return {"text": text, "chunks": rows}

    def retrieve_for_task(self, task_id: int, query_text: str) -> dict:
        return {"vectors": self.vector_store.similarity_search_by_task(query_text, task_id), "graph": self.graph.find_task_context(task_id)}

    def retrieve_for_user(self, user_id: int, query_text: str) -> dict:
        return {"vectors": self.vector_store.similarity_search_by_user(query_text, user_id), "graph": self.graph.find_user_context(user_id)}

    def retrieve_for_department(self, department_id: int, query_text: str) -> dict:
        return {"vectors": self.vector_store.similarity_search(query_text, 5), "graph": self.graph.find_department_risks(department_id)}

    def build_chat_context(self, question: str, user_id: int | None = None, department_id: int | None = None) -> dict:
        if user_id:
            return self.retrieve_for_user(user_id, question)
        if department_id:
            return self.retrieve_for_department(department_id, question)
        return {"vectors": self.vector_store.similarity_search(question, 5), "graph": self.graph.find_department_risks()}

    def _sync_graph(self, evidence: TaskEvidence, task: Task | None, chunks: list) -> None:
        self.graph.upsert_evidence(evidence)
        if task:
            self.graph.upsert_task(task)
            self.graph.link_task_evidence(task.id, evidence.id)
            for assignment in self.db.query(TaskAssignment).filter(TaskAssignment.task_id == task.id).all():
                self.graph.link_user_task(assignment.user_id, task.id)
        for chunk in chunks:
            self.graph.upsert_chunk(chunk)
            self.graph.link_evidence_chunk(evidence.id, chunk.id)
