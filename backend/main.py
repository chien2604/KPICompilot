"""
main.py – FastAPI application entry point cho Module 6.

Khởi động:
    uvicorn main:app --reload --port 8997

Hoặc chạy trực tiếp:
    python main.py
"""

from __future__ import annotations

# Force UTF-8 everywhere on Windows BEFORE any other imports
import os
os.environ.setdefault("PYTHONUTF8", "1")

import io
import logging
import sys
from contextlib import asynccontextmanager


import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

from config import settings
from routers.evidence import router as evidence_router

# ── Logging setup (UTF-8 safe on Windows) ────────────────────────────
# Force stdout to UTF-8 so Vietnamese/emoji chars don't crash on cp1252
_utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(_utf8_stdout)],
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Lifespan (startup / shutdown)
# ══════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo tài nguyên khi start, dọn dẹp khi shutdown."""
    # Startup
    settings.ensure_dirs()
    logger.info("=" * 60)
    logger.info("  AI KPI Copilot - Module 6: AI Phan tich Minh chung")
    logger.info("  Port        : %s", settings.api_service_port)
    logger.info("  Text model  : %s", settings.text_model)
    logger.info("  Vision model: %s", settings.vision_model)
    logger.info("  Upload dir  : %s", settings.upload_dir)
    logger.info("  Store file  : %s", settings.store_file)
    key_ok = (
        bool(settings.openrouter_api_key)
        and settings.openrouter_api_key != "your_openrouter_key_here"
    )
    logger.info("  OpenRouter  : %s", "[OK] Configured" if key_ok else "[!!] NOT configured - set OPENROUTER_API_KEY in .env")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("Server shutting down.")


# ══════════════════════════════════════════════════════════════════════
# App instance
# ══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="AI KPI Copilot - Module 6",
    description=(
        "**REST API** cho module **AI Phân tích Minh chứng**.\n\n"
        "Cán bộ tải lên file minh chứng (PDF, Word, Excel, ảnh). "
        "Hệ thống tự động trích xuất nội dung và dùng **OpenRouter AI** "
        "để đánh giá mức độ phù hợp với yêu cầu nhiệm vụ gốc.\n\n"
        "**Pipeline:**\n"
        "1. Upload → trích xuất text/ảnh\n"
        "2. Gửi OpenRouter (gpt-4.1-mini cho text, gpt-4o cho ảnh)\n"
        "3. Nhận điểm tương thích (0-100), checklist, nhận xét AI\n"
        "4. Poll `GET /api/evidence/{id}` để lấy kết quả"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler ──────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Lỗi máy chủ nội bộ", "detail": str(exc)},
    )


# ── Include Routers ───────────────────────────────────────────────────
app.include_router(evidence_router)


# ── Root ──────────────────────────────────────────────────────────────
@app.get("/", tags=["root"])
async def root():
    return {
        "app": "AI KPI Copilot",
        "module": "Module 6 – AI Phân tích Minh chứng",
        "version": "1.0.0",
        "docs": "/docs",
        "test_ui": "/test",
        "health": "/api/evidence/health",
    }


# ── Test UI (served from same origin to avoid CORS) ────────────────
@app.get("/test", response_class=HTMLResponse, tags=["root"], include_in_schema=False)
async def test_ui():
    """Serve test UI HTML at same origin – avoids CORS issue with file://"""
    html_path = Path(__file__).parent / "test_ui.html"
    if not html_path.exists():
        return HTMLResponse("<h1>test_ui.html not found</h1>", status_code=404)
    # Replace the hardcoded API base URL with empty string (same-origin)
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("const API = 'http://localhost:8997'", "const API = ''")
    return HTMLResponse(content=html)


# ══════════════════════════════════════════════════════════════════════
# Entrypoint
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_service_port,
        reload=True,
        log_level="info",
    )
