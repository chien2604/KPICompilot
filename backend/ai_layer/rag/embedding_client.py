import hashlib
import math
import random
from abc import ABC, abstractmethod

from core.config import get_settings


class BaseEmbeddingClient(ABC):
    dimensions = 1024

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


class MockEmbeddingClient(BaseEmbeddingClient):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
            rng = random.Random(seed)
            vector = [rng.uniform(-1, 1) for _ in range(self.dimensions)]
            norm = math.sqrt(sum(v * v for v in vector)) or 1
            vectors.append([v / norm for v in vector])
        return vectors


class BgeM3EmbeddingClient(BaseEmbeddingClient):
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer("BAAI/bge-m3")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        values = self.model.encode(texts, normalize_embeddings=True)
        return [list(map(float, row)) for row in values]


def get_embedding_client() -> BaseEmbeddingClient:
    if get_settings().use_real_embeddings:
        try:
            return BgeM3EmbeddingClient()
        except Exception:
            return MockEmbeddingClient()
    return MockEmbeddingClient()
