class TextChunker:
    def __init__(self, chunk_size: int = 900, overlap: int = 120) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[str]:
        cleaned = " ".join((text or "").split())
        if not cleaned:
            return ["Minh chứng chưa có nội dung text trích xuất được."]
        chunks: list[str] = []
        start = 0
        while start < len(cleaned):
            end = start + self.chunk_size
            chunks.append(cleaned[start:end])
            start = max(end - self.overlap, end) if end >= len(cleaned) else end - self.overlap
        return chunks
