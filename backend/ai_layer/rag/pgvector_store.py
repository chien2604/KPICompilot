from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_layer.rag.embedding_client import BaseEmbeddingClient, get_embedding_client
from db.models.rag import DocumentChunk
from db.models.tasks import TaskAssignment


class PGVectorStore:
    def __init__(self, db_session: Session, embedding_client: BaseEmbeddingClient | None = None) -> None:
        self.db = db_session
        self.embedding_client = embedding_client or get_embedding_client()

    def add_chunks(self, evidence_id: int, task_id: int, chunks: list[str], embeddings: list[list[float]]) -> list[DocumentChunk]:
        rows = []
        for index, (content, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
            row = DocumentChunk(
                evidence_id=evidence_id,
                task_id=task_id,
                chunk_index=index,
                content=content,
                embedding=embedding,
                metadata_json={"source": "evidence", "task_id": task_id},
            )
            self.db.add(row)
            rows.append(row)
        self.db.flush()
        return rows

    def similarity_search(self, query_text: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        query_vector = self.embedding_client.embed_query(query_text)
        stmt = select(DocumentChunk)
        filters = filters or {}
        if "task_id" in filters:
            stmt = stmt.where(DocumentChunk.task_id == filters["task_id"])
        if "evidence_id" in filters:
            stmt = stmt.where(DocumentChunk.evidence_id == filters["evidence_id"])
        stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(query_vector)).limit(top_k)
        return [self._to_source(row) for row in self.db.scalars(stmt).all()]

    def similarity_search_by_task(self, query_text: str, task_id: int, top_k: int = 5) -> list[dict]:
        return self.similarity_search(query_text, top_k, {"task_id": task_id})

    def similarity_search_by_user(self, query_text: str, user_id: int, top_k: int = 5) -> list[dict]:
        task_ids = self.db.scalars(select(TaskAssignment.task_id).where(TaskAssignment.user_id == user_id)).all()
        if not task_ids:
            return []
        query_vector = self.embedding_client.embed_query(query_text)
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.task_id.in_(task_ids))
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(top_k)
        )
        return [self._to_source(row) for row in self.db.scalars(stmt).all()]

    def _to_source(self, chunk: DocumentChunk) -> dict:
        return {
            "chunk_id": chunk.id,
            "evidence_id": chunk.evidence_id,
            "task_id": chunk.task_id,
            "content": chunk.content[:700],
        }
