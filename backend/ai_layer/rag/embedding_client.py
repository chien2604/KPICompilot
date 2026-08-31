import hashlib
import math
import random
from abc import ABC, abstractmethod

from core.config import get_settings


class BaseEmbeddingClient(ABC):
    """Represent base embedding client data and behavior."""

    dimensions = 1024

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Handle the texts."""

        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        """Handle the query."""

        return self.embed_texts([text])[0]


class MockEmbeddingClient(BaseEmbeddingClient):
    """Represent mock embedding client data and behavior."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Handle the texts."""

        vectors = []
        for text in texts:
            seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
            rng = random.Random(seed)
            vector = [rng.uniform(-1, 1) for _ in range(self.dimensions)]
            norm = math.sqrt(sum(v * v for v in vector)) or 1
            vectors.append([v / norm for v in vector])
        return vectors


class BgeM3EmbeddingClient(BaseEmbeddingClient):
    """Represent bge m3 embedding client data and behavior."""

    def __init__(self) -> None:
        """Initialize the bge m3 embedding client."""

        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer("BAAI/bge-m3")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Handle the texts."""

        values = self.model.encode(texts, normalize_embeddings=True)
        return [list(map(float, row)) for row in values]


def get_embedding_client() -> BaseEmbeddingClient:
    """Return the embedding client."""

    if get_settings().use_real_embeddings:
        try:
            return BgeM3EmbeddingClient()
        except Exception:
            return MockEmbeddingClient()
    return MockEmbeddingClient()
