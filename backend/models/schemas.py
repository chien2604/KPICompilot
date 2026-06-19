"""
models/schemas.py – Pydantic v2 schemas cho toàn bộ API.

Định nghĩa:
  - Request bodies (upload form, query params)
  - Response models (evidence record, analysis result)
  - Enums (file type, status)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ══════════════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════════════

class FileType(str, Enum):
    PDF   = "pdf"
    WORD  = "word"
    EXCEL = "excel"
    IMAGE = "image"
    OTHER = "other"


class AnalysisStatus(str, Enum):
    PENDING   = "pending"    # Mới upload, chưa phân tích
    ANALYZING = "analyzing"  # Đang gửi lên AI
    DONE      = "done"       # Phân tích xong
    ERROR     = "error"      # Lỗi trong quá trình phân tích


# ══════════════════════════════════════════════════════════════════════
# Checklist Item (mỗi tiêu chí kiểm tra)
# ══════════════════════════════════════════════════════════════════════

class ChecklistItem(BaseModel):
    """Một tiêu chí trong danh sách kiểm tra của AI."""
    item: str = Field(..., description="Tên tiêu chí kiểm tra")
    met: bool = Field(..., description="Tài liệu có đáp ứng tiêu chí này không")
    note: Optional[str] = Field(None, description="Ghi chú thêm của AI về tiêu chí này")
    deduction: int = Field(0, description="Điểm trừ khi tiêu chí này không đạt (0 nếu đạt)")
    importance: str = Field("minor", description="Độ quan trọng của tiêu chí (core hoặc minor)")


# ══════════════════════════════════════════════════════════════════════
# Analysis Result
# ══════════════════════════════════════════════════════════════════════

class AnalysisResult(BaseModel):
    """Kết quả phân tích AI trả về cho một file minh chứng."""

    compatibility_score: int = Field(
        ...,
        ge=0, le=100,
        description="Điểm tương thích tổng thể (0–100)",
    )
    checklist: list[ChecklistItem] = Field(
        default_factory=list,
        description="Danh sách tiêu chí kiểm tra từng mục",
    )
    ai_comment: str = Field(
        ...,
        description="Nhận xét tổng hợp của AI về tài liệu",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Điểm mạnh của tài liệu theo AI",
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="Điểm cần cải thiện / thiếu sót",
    )
    extracted_text_length: int = Field(
        0,
        description="Số ký tự được trích xuất từ tài liệu",
    )
    model_used: str = Field(
        "",
        description="Model AI đã dùng để phân tích",
    )
    analyzed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Thời điểm phân tích hoàn tất (UTC)",
    )

    @field_validator("compatibility_score")
    @classmethod
    def clamp_score(cls, v: int) -> int:
        return max(0, min(100, v))


# ══════════════════════════════════════════════════════════════════════
# Evidence Record (lưu trong JSON store)
# ══════════════════════════════════════════════════════════════════════

class EvidenceRecord(BaseModel):
    """Bản ghi đầy đủ cho một file minh chứng (lưu trong JSON store)."""

    id: str = Field(..., description="UUID duy nhất")
    filename: str = Field(..., description="Tên file gốc")
    stored_filename: str = Field(..., description="Tên file đã lưu trong uploads/")
    file_type: FileType = Field(..., description="Loại file")
    file_size: int = Field(..., description="Kích thước file (bytes)")
    mime_type: str = Field("", description="MIME type")

    # Thông tin nhiệm vụ liên quan
    task_name: str = Field(..., description="Tên nhiệm vụ cần minh chứng")
    task_description: str = Field("", description="Mô tả chi tiết nhiệm vụ / yêu cầu")
    task_deadline: str = Field("", description="Hạn chót nhiệm vụ")
    task_weight: int = Field(10, ge=1, le=100, description="Trọng số nhiệm vụ (%)")

    # Người nộp
    uploader_name: str = Field(..., description="Tên cán bộ nộp minh chứng")
    department: str = Field("", description="Phòng ban")

    # Timestamps
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    # Trạng thái & kết quả AI
    status: AnalysisStatus = Field(AnalysisStatus.PENDING)
    error_message: Optional[str] = Field(None)
    analysis: Optional[AnalysisResult] = Field(None)


# ══════════════════════════════════════════════════════════════════════
# API Response Wrappers
# ══════════════════════════════════════════════════════════════════════

class EvidenceSummary(BaseModel):
    """Phiên bản rút gọn dùng trong danh sách (GET /api/evidence/)."""
    id: str
    filename: str
    file_type: FileType
    file_size: int
    task_name: str
    uploader_name: str
    department: str
    uploaded_at: datetime
    status: AnalysisStatus
    compatibility_score: Optional[int] = None


class UploadResponse(BaseModel):
    """Phản hồi sau khi upload thành công."""
    id: str
    filename: str
    status: AnalysisStatus
    message: str


class ListResponse(BaseModel):
    """Phản hồi cho endpoint danh sách."""
    total: int
    items: list[EvidenceSummary]


class ErrorResponse(BaseModel):
    """Phản hồi lỗi chuẩn."""
    error: str
    detail: Optional[str] = None
