"""
routers/evidence.py – API Router cho Module 6: AI Phân tích Minh chứng.

Endpoints:
  GET    /api/evidence/health          – Health check
  POST   /api/evidence/upload          – Upload file + metadata
  GET    /api/evidence/                – Danh sách minh chứng
  GET    /api/evidence/{id}            – Chi tiết + kết quả AI
  POST   /api/evidence/{id}/analyze    – Kích hoạt phân tích lại
  DELETE /api/evidence/{id}            – Xóa minh chứng
  GET    /api/evidence/{id}/download   – Tải file về
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from config import settings
from models.schemas import (
    AnalysisStatus,
    EvidenceRecord,
    ErrorResponse,
    ListResponse,
    UploadResponse,
)
from services import ai_analyzer, extractor, storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


# ══════════════════════════════════════════════════════════════════════
# Background task: chạy phân tích AI
# ══════════════════════════════════════════════════════════════════════

async def _run_analysis(record_id: str) -> None:
    """
    Background task – được gọi sau khi upload xong.
    1. Đọc record từ store
    2. Trích xuất nội dung file
    3. Gọi OpenRouter AI
    4. Lưu kết quả
    """
    # Đánh dấu đang phân tích
    await storage.update_status(record_id, AnalysisStatus.ANALYZING)

    record = await storage.get_record(record_id)
    if record is None:
        logger.error("Background task: record %s không tồn tại", record_id)
        return

    try:
        # Bước 1: Trích xuất nội dung
        file_path = storage.get_upload_path(record.stored_filename)
        extraction = extractor.extract(file_path, record.file_type.value)

        if extraction.get("error"):
            logger.warning(
                "Extraction warning for %s: %s",
                record.filename, extraction["error"],
            )
            # Vẫn tiếp tục nếu có partial content
            if not extraction.get("text") and not extraction.get("image_b64"):
                await storage.update_status(
                    record_id,
                    AnalysisStatus.ERROR,
                    error=extraction["error"],
                )
                return

        # Bước 2: Phân tích AI
        result = await ai_analyzer.analyze(
            filename=record.filename,
            file_type=record.file_type.value,
            extracted_text=extraction.get("text", ""),
            image_b64=extraction.get("image_b64", ""),
            page_count=extraction.get("page_count", 1),
            is_image=extraction.get("is_image", False),
            task_name=record.task_name,
            task_description=record.task_description,
            task_deadline=record.task_deadline,
            uploader_name=record.uploader_name,
            department=record.department,
        )

        # Bước 3: Lưu kết quả
        await storage.save_analysis(record_id, result)
        logger.info(
            "Analysis complete for %s: score=%d",
            record.filename, result.compatibility_score,
        )

    except Exception as exc:  # noqa: BLE001
        err_msg = f"Lỗi pipeline phân tích: {exc}"
        logger.exception(err_msg)
        await storage.update_status(record_id, AnalysisStatus.ERROR, error=err_msg)


# ══════════════════════════════════════════════════════════════════════
# Validation helpers
# ══════════════════════════════════════════════════════════════════════

def _validate_file(file: UploadFile, file_bytes: bytes) -> None:
    """Kiểm tra kích thước và định dạng file."""
    # Kiểm tra kích thước
    if len(file_bytes) > settings.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File quá lớn. Tối đa {settings.max_file_size // 1_048_576} MB.",
        )

    # Kiểm tra extension
    if file.filename:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in settings.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Định dạng file '{suffix}' không được hỗ trợ. "
                       f"Hỗ trợ: {', '.join(sorted(settings.allowed_extensions))}",
            )

    # Kiểm tra MIME type
    content_type = file.content_type or ""
    if content_type and content_type not in settings.allowed_mime_types:
        # Một số trình duyệt gửi sai MIME, chỉ cảnh báo không chặn
        logger.warning("MIME type không quen thuộc: %s", content_type)


# ══════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════

@router.get("/health", summary="Health check")
async def health_check():
    """Kiểm tra server đang hoạt động."""
    return {
        "status": "ok",
        "module": "Module 6 – AI Phân tích Minh chứng",
        "version": "1.0.0",
        "openrouter_configured": bool(
            settings.openrouter_api_key
            and settings.openrouter_api_key != "your_openrouter_key_here"
        ),
        "text_model": settings.text_model,
        "vision_model": settings.vision_model,
    }


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file minh chứng",
    description=(
        "Upload file (PDF/Word/Excel/ảnh) kèm thông tin nhiệm vụ. "
        "Phân tích AI sẽ chạy trong nền, poll GET /{id} để lấy kết quả."
    ),
)
async def upload_evidence(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="File minh chứng (PDF/DOCX/XLSX/ảnh)"),
    task_name: str = Form(..., description="Tên nhiệm vụ cần minh chứng"),
    task_description: str = Form("", description="Mô tả / yêu cầu chi tiết của nhiệm vụ"),
    task_deadline: str = Form("", description="Hạn chót (dd/MM/yyyy)"),
    uploader_name: str = Form(..., description="Tên cán bộ nộp minh chứng"),
    department: str = Form("", description="Phòng ban"),
):
    # Đọc file bytes
    file_bytes = await file.read()
    _validate_file(file, file_bytes)

    # Lưu file vật lý
    stored_name, file_type, file_size = await storage.save_upload_file(
        file_bytes=file_bytes,
        original_filename=file.filename or "unknown",
    )

    # Tạo bản ghi trong store
    record = await storage.create_record(
        original_filename=file.filename or "unknown",
        stored_filename=stored_name,
        file_type=file_type,
        file_size=file_size,
        mime_type=file.content_type or "",
        task_name=task_name,
        task_description=task_description,
        task_deadline=task_deadline,
        uploader_name=uploader_name,
        department=department,
    )

    # Kích hoạt phân tích AI trong nền
    background_tasks.add_task(_run_analysis, record.id)

    logger.info("Uploaded: %s (id=%s), type=%s", file.filename, record.id, file_type)

    return UploadResponse(
        id=record.id,
        filename=record.filename,
        status=AnalysisStatus.PENDING,
        message="Upload thành công! AI đang phân tích tài liệu, vui lòng đợi 10–30 giây.",
    )


@router.get(
    "/",
    response_model=ListResponse,
    summary="Danh sách minh chứng",
)
async def list_evidence(
    status_filter: str | None = None,
    file_type_filter: str | None = None,
):
    """
    Lấy danh sách toàn bộ minh chứng.
    Có thể lọc theo `status` (pending/analyzing/done/error) và `file_type` (pdf/word/excel/image).
    """
    records = await storage.list_records()

    if status_filter:
        records = [r for r in records if r.status.value == status_filter]
    if file_type_filter:
        records = [r for r in records if r.file_type.value == file_type_filter]

    summaries = [storage.to_summary(r) for r in records]
    return ListResponse(total=len(summaries), items=summaries)


@router.get(
    "/{record_id}",
    response_model=EvidenceRecord,
    summary="Chi tiết minh chứng + kết quả AI",
    responses={404: {"model": ErrorResponse}},
)
async def get_evidence(record_id: str):
    """
    Lấy chi tiết một minh chứng theo ID, bao gồm toàn bộ kết quả phân tích AI.
    Dùng để **poll** sau khi upload cho đến khi `status == 'done'`.
    """
    record = await storage.get_record(record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy minh chứng với id: {record_id}",
        )
    return record


@router.post(
    "/{record_id}/analyze",
    response_model=UploadResponse,
    summary="Kích hoạt phân tích AI lại",
    responses={404: {"model": ErrorResponse}},
)
async def re_analyze(record_id: str, background_tasks: BackgroundTasks):
    """
    Chạy lại phân tích AI cho một minh chứng đã upload.
    Hữu ích khi lần đầu bị lỗi hoặc muốn cập nhật kết quả.
    """
    record = await storage.get_record(record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy minh chứng với id: {record_id}",
        )

    if record.status == AnalysisStatus.ANALYZING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tài liệu đang được phân tích, vui lòng đợi.",
        )

    # Reset về pending rồi chạy lại
    await storage.update_status(record_id, AnalysisStatus.PENDING)
    background_tasks.add_task(_run_analysis, record_id)

    return UploadResponse(
        id=record.id,
        filename=record.filename,
        status=AnalysisStatus.PENDING,
        message="Đã kích hoạt phân tích lại. Poll GET /{id} để lấy kết quả.",
    )


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa minh chứng",
    responses={404: {"model": ErrorResponse}},
)
async def delete_evidence(record_id: str):
    """Xóa minh chứng khỏi store và file vật lý trên server."""
    deleted = await storage.delete_record(record_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy minh chứng với id: {record_id}",
        )
    logger.info("Deleted evidence: %s", record_id)


@router.get(
    "/{record_id}/download",
    summary="Tải file minh chứng về",
    responses={404: {"model": ErrorResponse}},
)
async def download_evidence(record_id: str):
    """Tải file gốc về từ server."""
    record = await storage.get_record(record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy minh chứng với id: {record_id}",
        )

    file_path = storage.get_upload_path(record.stored_filename)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="File vật lý không còn tồn tại trên server.",
        )

    media_type, _ = mimetypes.guess_type(record.filename)
    return FileResponse(
        path=str(file_path),
        filename=record.filename,
        media_type=media_type or "application/octet-stream",
    )
