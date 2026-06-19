"""
config.py – Cấu hình tập trung cho toàn bộ backend Module 6.
Đọc biến môi trường từ file .env (hoặc hệ thống).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── OpenRouter ────────────────────────────────────────────────
    openrouter_api_key: str = "your_openrouter_key_here"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # ── Google Gemini ─────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── Groq ──────────────────────────────────────────────────────
    groq_api_key: str = ""

    # Model text (không cần vision)
    text_model: str = "openai/gpt-4.1-mini"
    # Model vision (dùng khi file là ảnh)
    vision_model: str = "openai/gpt-4o"

    # ── Server ────────────────────────────────────────────────────
    api_service_port: int = 8997
    api_host: str = "0.0.0.0"

    # ── CORS ──────────────────────────────────────────────────────
    cors_origins: str = (
        "http://localhost:3000,"
        "http://localhost:5173,"
        "http://127.0.0.1:5500,"
        "http://localhost:8080"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── Storage ───────────────────────────────────────────────────
    upload_dir: str = "./uploads"
    store_file: str = "./data/evidence_store.json"

    # Kích thước file tối đa (bytes) – mặc định 30 MB
    max_file_size: int = 31_457_280

    # ── Loại file được phép ───────────────────────────────────────
    allowed_extensions: set[str] = {
        ".pdf", ".docx", ".doc", ".xlsx", ".xls",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    }
    allowed_mime_types: set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/bmp",
        "image/webp",
    }

    def ensure_dirs(self) -> None:
        """Tạo thư mục cần thiết nếu chưa có."""
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.store_file).parent.mkdir(parents=True, exist_ok=True)


# Singleton – import từ các module khác
settings = Settings()
