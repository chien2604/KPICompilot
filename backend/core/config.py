from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "AI KPI Copilot for Government"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://kpi:kpi@localhost:5433/kpi_government"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_site_url: str = "http://localhost:5180"
    openrouter_app_name: str = "AI KPI Copilot for Government"
    use_real_embeddings: bool = False
    storage_dir: Path = BASE_DIR / "storage"
    upload_dir: Path = BASE_DIR / "storage" / "uploads"
    kuzu_db_path: Path = BASE_DIR / "storage" / "kuzu_db"
    cors_origins: str = "http://localhost:5180,http://127.0.0.1:5180"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.kuzu_db_path.mkdir(parents=True, exist_ok=True)
    return settings