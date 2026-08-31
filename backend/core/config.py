from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    """Centralize runtime configuration and filesystem locations."""

    app_name: str = "AI KPI Copilot for Government"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://kpi:kpi@localhost:5433/kpi_government"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_site_url: str = "http://localhost:5191"
    openrouter_app_name: str = "AI KPI Copilot for Government"
    use_real_embeddings: bool = False
    storage_dir: Path = BASE_DIR / "storage"
    upload_dir: Path = BASE_DIR / "storage" / "uploads"
    kuzu_db_path: Path = BASE_DIR / "storage" / "kuzu_db"
    import_dir: Path = BASE_DIR / "storage" / "imports"
    personnel_import_path: Path = (
        PROJECT_DIR / "Danh sách CB, CC , VC đến ngày 01.8.2026.xlsx"
    )
    work_catalog_import_path: Path = PROJECT_DIR / "DM công việc gửi kèm QĐ 15.6.xlsx"
    organization_name: str = "Ủy ban nhân dân xã Nghĩa Lâm"
    organization_code: str = "UBND_XA_NGHIA_LAM"
    bootstrap_admin_name: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    smoke_test_base_url: str = "http://localhost:8017"
    smoke_test_email: str | None = None
    smoke_test_password: str | None = None
    cors_origins: str = "http://localhost:5191,http://127.0.0.1:5191"
    jwt_secret_key: str = "change-me-in-production-super-secret-key-kpi-copilot"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 ngày

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Load cached settings and ensure writable storage directories exist."""

    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.kuzu_db_path.mkdir(parents=True, exist_ok=True)
    settings.import_dir.mkdir(parents=True, exist_ok=True)
    return settings
