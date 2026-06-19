from pathlib import Path

class DocumentLoader:
    def extract_text(self, file_path: str) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()
        try:
            if suffix in {".txt", ".md", ".csv"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
            elif suffix == ".pdf":
                text = self._extract_pdf(path)
            elif suffix == ".docx":
                text = self._extract_docx(path)
            elif suffix in {".xlsx", ".xls"}:
                text = self._extract_excel(path)
            else:
                # Không đọc trực tiếp file nhị phân chưa hỗ trợ thành text
                text = f"Đã upload file {path.name} định dạng {suffix} chưa được hỗ trợ trích xuất toàn văn."
        except Exception:
            text = f"Không đọc được nội dung file {path.name}. Dùng metadata file làm minh chứng demo."
        
        # Bắt buộc: Loại bỏ ký tự null (\x00) vì PostgreSQL không chấp nhận ký tự này trong trường TEXT
        return text.replace("\x00", "")

    def _extract_excel(self, path: Path) -> str:
        try:
            import pandas as pd
            df_dict = pd.read_excel(str(path), sheet_name=None)
            text_parts = []
            for sheet_name, df in df_dict.items():
                text_parts.append(f"--- Sheet: {sheet_name} ---")
                text_parts.append(df.to_csv(index=False, sep='\t'))
            return "\n".join(text_parts)
        except Exception:
            return f"EXCEL {path.name} đã được upload nhưng chưa trích xuất được text."

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
