"""
services/storage.py – Quản lý JSON store và file hệ thống.

Chức năng:
  - Đọc/ghi evidence_store.json (thread-safe với asyncio.Lock)
  - Lưu file upload vào thư mục uploads/
  - CRUD operations trên EvidenceRecord
"""

from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from config import settings
from models.schemas import (
    AnalysisResult,
    AnalysisStatus,
    EvidenceRecord,
    EvidenceSummary,
    FileType,
)

# Lock ngăn race condition khi nhiều request ghi file JSON cùng lúc
_store_lock = asyncio.Lock()


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

def _ext_to_file_type(ext: str) -> FileType:
    """Chuyển đuôi file sang FileType enum."""
    ext = ext.lower()
    if ext == ".pdf":
        return FileType.PDF
    if ext in {".docx", ".doc"}:
        return FileType.WORD
    if ext in {".xlsx", ".xls"}:
        return FileType.EXCEL
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
        return FileType.IMAGE
    return FileType.OTHER


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


# ══════════════════════════════════════════════════════════════════════
# JSON Store
# ══════════════════════════════════════════════════════════════════════

async def _read_store() -> dict[str, dict]:
    """Đọc toàn bộ store từ JSON file."""
    store_path = Path(settings.store_file)
    if not store_path.exists():
        return {}
    async with aiofiles.open(store_path, "r", encoding="utf-8") as f:
        content = await f.read()
    if not content.strip():
        return {}
    return json.loads(content)


async def _write_store(data: dict[str, dict]) -> None:
    """Ghi toàn bộ store ra JSON file."""
    store_path = Path(settings.store_file)
    async with aiofiles.open(store_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2, default=str))


# ══════════════════════════════════════════════════════════════════════
# File Operations
# ══════════════════════════════════════════════════════════════════════

async def save_upload_file(
    file_bytes: bytes,
    original_filename: str,
) -> tuple[str, str, int]:
    """
    Lưu file upload vào thư mục uploads/.

    Returns:
        (stored_filename, file_type_str, file_size)
    """
    settings.ensure_dirs()

    suffix = Path(original_filename).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    dest = Path(settings.upload_dir) / stored_name

    async with aiofiles.open(dest, "wb") as f:
        await f.write(file_bytes)

    file_type = _ext_to_file_type(suffix)
    return stored_name, file_type.value, len(file_bytes)


def delete_upload_file(stored_filename: str) -> None:
    """Xóa file vật lý trong uploads/."""
    path = Path(settings.upload_dir) / stored_filename
    if path.exists():
        path.unlink()


def get_upload_path(stored_filename: str) -> Path:
    """Trả về đường dẫn tuyệt đối của file đã lưu."""
    return Path(settings.upload_dir) / stored_filename


# ══════════════════════════════════════════════════════════════════════
# CRUD
# ══════════════════════════════════════════════════════════════════════

async def create_record(
    *,
    original_filename: str,
    stored_filename: str,
    file_type: str,
    file_size: int,
    mime_type: str,
    task_name: str,
    task_description: str,
    task_deadline: str,
    uploader_name: str,
    department: str,
) -> EvidenceRecord:
    """Tạo bản ghi mới và lưu vào store."""
    record = EvidenceRecord(
        id=uuid.uuid4().hex,
        filename=original_filename,
        stored_filename=stored_filename,
        file_type=FileType(file_type),
        file_size=file_size,
        mime_type=mime_type,
        task_name=task_name,
        task_description=task_description,
        task_deadline=task_deadline,
        uploader_name=uploader_name,
        department=department,
        status=AnalysisStatus.PENDING,
    )

    async with _store_lock:
        store = await _read_store()
        store[record.id] = record.model_dump(mode="json")
        await _write_store(store)

    return record


async def get_record(record_id: str) -> Optional[EvidenceRecord]:
    """Lấy một bản ghi theo ID."""
    async with _store_lock:
        store = await _read_store()
    raw = store.get(record_id)
    if raw is None:
        return None
    return EvidenceRecord.model_validate(raw)


async def list_records() -> list[EvidenceRecord]:
    """Lấy toàn bộ bản ghi, sắp xếp mới nhất trước."""
    async with _store_lock:
        store = await _read_store()
    records = [EvidenceRecord.model_validate(v) for v in store.values()]
    records.sort(key=lambda r: r.uploaded_at, reverse=True)
    return records


async def update_status(record_id: str, status: AnalysisStatus, error: str = "") -> None:
    """Cập nhật trạng thái phân tích."""
    async with _store_lock:
        store = await _read_store()
        if record_id not in store:
            return
        store[record_id]["status"] = status.value
        if error:
            store[record_id]["error_message"] = error
        await _write_store(store)


async def save_analysis(record_id: str, result: AnalysisResult) -> Optional[EvidenceRecord]:
    """Lưu kết quả phân tích AI vào bản ghi."""
    async with _store_lock:
        store = await _read_store()
        if record_id not in store:
            return None
        store[record_id]["status"] = AnalysisStatus.DONE.value
        store[record_id]["analysis"] = result.model_dump(mode="json")
        store[record_id]["error_message"] = None
        await _write_store(store)
        return EvidenceRecord.model_validate(store[record_id])


async def delete_record(record_id: str) -> bool:
    """Xóa bản ghi khỏi store và file vật lý."""
    async with _store_lock:
        store = await _read_store()
        if record_id not in store:
            return False
        stored_fn = store[record_id].get("stored_filename", "")
        del store[record_id]
        await _write_store(store)

    if stored_fn:
        delete_upload_file(stored_fn)
    return True


def to_summary(record: EvidenceRecord) -> EvidenceSummary:
    """Chuyển EvidenceRecord thành EvidenceSummary cho danh sách."""
    score = None
    if record.analysis:
        score = record.analysis.compatibility_score
    return EvidenceSummary(
        id=record.id,
        filename=record.filename,
        file_type=record.file_type,
        file_size=record.file_size,
        task_name=record.task_name,
        uploader_name=record.uploader_name,
        department=record.department,
        uploaded_at=record.uploaded_at,
        status=record.status,
        compatibility_score=score,
    )
