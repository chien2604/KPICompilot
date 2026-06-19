from pathlib import Path


class DocumentLoader:
    def extract_text(self, file_path: str) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()
        try:
            if suffix in {".txt", ".md", ".csv"}:
                return path.read_text(encoding="utf-8", errors="ignore")
            if suffix == ".pdf":
                return self._extract_pdf(path)
            if suffix == ".docx":
                return self._extract_docx(path)
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return f"Không đọc được nội dung file {path.name}. Dùng metadata file làm minh chứng demo."

    def _extract_pdf(self, path: Path) -> str:
        try:
            from docling.document_converter import DocumentConverter

            result = DocumentConverter().convert(str(path))
            return result.document.export_to_markdown()
        except Exception:
            try:
                from pypdf import PdfReader

                reader = PdfReader(str(path))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                return f"PDF {path.name} đã được upload nhưng chưa trích xuất được text."

    def _extract_docx(self, path: Path) -> str:
        try:
            from docling.document_converter import DocumentConverter

            result = DocumentConverter().convert(str(path))
            return result.document.export_to_markdown()
        except Exception:
            try:
                from docx import Document

                doc = Document(str(path))
                return "\n".join(p.text for p in doc.paragraphs)
            except Exception:
                return f"DOCX {path.name} đã được upload nhưng chưa trích xuất được text."
