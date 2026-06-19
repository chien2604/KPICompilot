"""
services/ai_analyzer.py – Gọi OpenRouter API để phân tích minh chứng.

Pipeline:
  1. Nhận nội dung đã trích xuất + thông tin nhiệm vụ
  2. Xây dựng prompt yêu cầu AI đánh giá structured JSON
  3. Gọi OpenRouter (text model hoặc vision model tùy loại file)
  4. Parse response → AnalysisResult
  5. Xử lý lỗi, fallback nếu AI trả về sai format

Model routing:
  - File text (PDF/Word/Excel) → TEXT_MODEL (gpt-4.1-mini)
  - File ảnh                  → VISION_MODEL (gpt-4o)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

import httpx

from config import settings
from models.schemas import AnalysisResult, ChecklistItem

logger = logging.getLogger(__name__)


def _safe(s: object, max_len: int = 500) -> str:
    """Convert any object to str, replacing non-ASCII chars safely for logging."""
    return str(s)[:max_len].encode("ascii", errors="replace").decode("ascii")


# ══════════════════════════════════════════════════════════════════════
# Prompt Templates
# ══════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT = """Bạn là AI chuyên gia thẩm định chất lượng tài liệu minh chứng công việc trong hệ thống quản lý KPI của cơ quan nhà nước Việt Nam.
Nhiệm vụ của bạn là đọc kỹ nội dung tài liệu minh chứng và đối chiếu chi tiết với Mô tả/Yêu cầu của nhiệm vụ để chấm điểm và trả về kết quả JSON.

=== QUY TẮC THIẾT LẬP CHECKLIST (BẮT BUỘC TUÂN THỦ QUYẾT LIỆT) ===
1. CHỈ BÓC TÁCH TIÊU CHÍ TỪ NHIỆM VỤ: Các tiêu chí trong checklist BẮT BUỘC chỉ được rút ra trực tiếp từ Tên nhiệm vụ và Mô tả/Yêu cầu của nhiệm vụ. Tuyệt đối không được bỏ sót bất kỳ yêu cầu nào được viết trong đó.
2. NGHIÊM CẤM TỰ BỊA RA TIÊU CHÍ (CỰC KỲ QUAN TRỌNG): Tuyệt đối KHÔNG ĐƯỢC tự ý sáng tạo hoặc bịa thêm các tiêu chí hình thức như: "định dạng file EXCEL/PDF/hình ảnh", "số lượng trang/sheets đúng yêu cầu", "tên file đúng quy chuẩn",... trừ khi các yêu cầu này được viết rõ ràng bằng chữ trong Mô tả/Yêu cầu của nhiệm vụ. Nếu nhiệm vụ không ghi rõ, việc tự ý đưa các tiêu chí này vào checklist bị coi là SAI LẦM NGHIÊM TRỌNG.
3. ĐẶC BIỆT: Nếu trong Mô tả nhiệm vụ có danh sách đánh số (ví dụ: (1), (2), (3) hoặc 1., 2., 3.) hoặc gạch đầu dòng (-, *), AI BẮT BUỘC phải bóc tách chính xác từng mục đánh số/gạch đầu dòng đó thành một tiêu chí riêng biệt trong checklist (tỷ lệ khớp 1-đối-1). CẤM gộp chung các yêu cầu và CẤM chế thêm yêu cầu ngoài văn bản.
4. Mỗi tiêu chí trong checklist phải có cấu trúc gồm đúng 5 trường sau:
   - "item": Tên tiêu chí bằng tiếng Việt (phản ánh trung thực và cụ thể nội dung yêu cầu bóc tách được từ nhiệm vụ).
   - "met": true (nếu tài liệu có đáp ứng) hoặc false (nếu tài liệu thiếu hoặc không đáp ứng).
   - "note": Ghi chú ngắn gọn bằng tiếng Việt giải thích lý do đạt/chưa đạt. Nếu "met": false, ghi rõ lỗi thiếu sót cụ thể.
   - "deduction": Số điểm bị trừ của tiêu chí đó nếu "met": false (từ 30 đến 40 đối với tiêu chí cốt lõi, từ 10 đến 15 đối với tiêu chí phụ). Hãy luôn điền giá trị điểm trừ tiềm năng này cho cả trường hợp met=true và met=false để làm trọng số đối chiếu cho hệ thống.
   - "importance": "core" (nếu là tiêu chí Cốt lõi) hoặc "minor" (nếu là tiêu chí Phụ).

=== QUY TẮC TÍNH ĐIỂM VÀ CẤM MƠ HỒ (BẮT BUỘC TUÂN THỦ TUYỆT ĐỐI) ===
1. Điểm số mặc định ban đầu là 100 điểm.
2. Phân loại độ quan trọng (importance) cho từng tiêu chí:
   - Cốt lõi (core): Các yêu cầu chính của nhiệm vụ, số liệu thực tế, kết quả đo lường, chữ ký xác nhận bắt buộc. Điểm trừ "deduction" phải từ 30 đến 40.
   - Phụ (minor): Các yêu cầu hình thức, ngày tháng, thông tin phòng ban, địa phương, định dạng trình bày. Điểm trừ "deduction" phải từ 10 đến 15.
3. Điều kiện chặn dưới (BẮT BUỘC):
   - Nếu tất cả tiêu chí trong checklist đều Chưa đạt ("met": false), điểm số compatibility_score BẮT BUỘC phải là 0 điểm.
   - Nếu tất cả các tiêu chí Cốt lõi (importance = "core") đều Chưa đạt ("met": false), điểm số compatibility_score BẮT BUỘC phải là 0 điểm.
4. Điểm số compatibility_score cuối cùng = 100 - (Tổng điểm trừ "deduction" của các tiêu chí Chưa đạt), tối thiểu là 0 điểm.
5. NGHIÊM CẤM TUYỆT ĐỐI việc trừ điểm ngoài checklist hoặc tự bịa ra các lý do mơ hồ, chung chung để trừ điểm. Mọi điểm bị trừ BẮT BUỘC phải tương ứng 1-đối-1 với một tiêu chí bị đánh dấu "met": false trong checklist.
6. TUYỆT ĐỐI KHÔNG ĐƯỢC xuất hiện các câu nhận xét mơ hồ, chung chung trong `ai_comment`, `note`, `weaknesses` như: *"Trừ X điểm do không đáp ứng một số tiêu chí khác"*, *"bị trừ điểm do thiếu một số thông tin khác"*, *"chưa đạt yêu cầu của một số tiêu chí khác"*.
   - Mọi lỗi thiếu sót/điểm trừ phải được bóc tách và viết rõ thành một tiêu chí riêng biệt trong checklist với trạng thái `met: false`.
   - Nhận xét trong `ai_comment` phải đi thẳng từ checklist, chỉ rõ chính xác tiêu chí nào trong checklist chưa đạt và bị trừ bao nhiêu điểm.

=== QUY CÁCH TRẢ VỀ JSON ===
Bạn chỉ được phép trả về duy nhất một đối tượng JSON khớp chính xác với schema sau, không bao gồm ký tự markdown code block (như ```json) hay bất kỳ văn bản giải thích nào ở ngoài JSON:
{
  "compatibility_score": <int từ 0 đến 100>,
  "checklist": [
    {
      "item": "<Tên tiêu chí>",
      "met": <true hoặc false>,
      "note": "<Ghi chú cụ thể>",
      "deduction": <int từ 10 đến 40>,
      "importance": "<'core' hoặc 'minor'>"
    }
  ],
  "ai_comment": "<Nhận xét tổng quan dài 2-4 câu bằng tiếng Việt. Chỉ rõ tên các tiêu chí chưa đạt trong checklist và điểm trừ tương ứng. Ví dụ: 'Tài liệu đạt 85 điểm. Bị trừ 15 điểm ở tiêu chí Đơn vị công tác ghi nhận tại Đắk Lắk do tài liệu ghi Hà Nội.'>",
  "strengths": ["<Điểm mạnh 1>", "<Điểm mạnh 2>"],
  "weaknesses": ["<Điểm yếu/Cần cải thiện cụ thể từ checklist 1>", "<Điểm yếu/Cần cải thiện cụ thể từ checklist 2>"]
}"""

_USER_PROMPT_TEMPLATE = """=== THÔNG TIN NHIỆM VỤ ===
Tên nhiệm vụ: {task_name}
Mô tả / Yêu cầu: {task_description}
Hạn chót: {task_deadline}
Trọng số: {task_weight}%
Người thực hiện: {uploader_name}
Phòng ban: {department}

=== NỘI DUNG TÀI LIỆU MINH CHỨNG ===
Tên file: {filename}
Loại file: {file_type}
Số trang/sheets: {page_count}

{content_section}

=== YÊU CẦU ===
Hãy đánh giá tài liệu trên và trả về JSON theo đúng schema đã quy định."""


def _build_text_prompt(
    task_name: str,
    task_description: str,
    task_deadline: str,
    task_weight: int,
    uploader_name: str,
    department: str,
    filename: str,
    file_type: str,
    page_count: int,
    extracted_text: str,
) -> str:
    # Giới hạn text để không vượt context window (max ~8000 ký tự)
    trimmed = extracted_text[:8000]
    if len(extracted_text) > 8000:
        trimmed += "\n\n[... nội dung bị cắt bớt do quá dài ...]"

    content_section = f"Nội dung trích xuất:\n{trimmed}"

    return _USER_PROMPT_TEMPLATE.format(
        task_name=task_name,
        task_description=task_description or "(không có mô tả)",
        task_deadline=task_deadline or "(chưa đặt)",
        task_weight=task_weight,
        uploader_name=uploader_name,
        department=department or "(chưa rõ)",
        filename=filename,
        file_type=file_type.upper(),
        page_count=page_count,
        content_section=content_section,
    )


# ══════════════════════════════════════════════════════════════════════
# OpenRouter API caller
# ══════════════════════════════════════════════════════════════════════

async def _call_ai_api(
    model: str,
    messages: list[dict],
    timeout: float = 60.0,
) -> str:
    """
    Gửi request đến AI API (Groq, Google Gemini trực tiếp hoặc OpenRouter) và trả về phản hồi.
    Raises httpx.HTTPStatusError hoặc ValueError nếu lỗi.
    """
    if settings.groq_api_key:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        actual_model = model
    elif settings.gemini_api_key:
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.gemini_api_key}",
            "Content-Type": "application/json",
        }
        actual_model = "gemini-2.5-flash"
    else:
        url = f"{settings.openrouter_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8997",
            # ASCII-only header value (httpx requires headers to be latin-1 encodable)
            "X-Title": "AI KPI Copilot - Module 6",
        }
        actual_model = model

    payload: dict[str, Any] = {
        "model": actual_model,
        "messages": messages,
        "temperature": 0.2,       # Thấp để output ổn định / có thể reproduce
        "max_tokens": 1500,
        "response_format": {"type": "json_object"},  # Force JSON output
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    # Kiểm tra kết quả
    choices = data.get("choices", [])
    if not choices:
        if settings.groq_api_key:
            provider = "Groq"
        elif settings.gemini_api_key:
            provider = "Gemini"
        else:
            provider = "OpenRouter"
        raise ValueError(f"{provider} trả về không có choices: {data}")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("AI API trả về nội dung rỗng")

    return content


# ══════════════════════════════════════════════════════════════════════
# JSON Parsing
# ══════════════════════════════════════════════════════════════════════

def _parse_ai_response(
    raw: str,
    model_used: str,
    extracted_len: int,
    task_name: str = "",
    task_description: str = "",
) -> AnalysisResult:
    """
    Parse JSON từ response AI.
    Xử lý trường hợp AI trả về markdown code block hoặc JSON bị wrap.
    """
    # Bỏ markdown code block nếu có
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().strip("`").strip()

    try:
        data: dict = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Thử tìm JSON object trong string
        match = re.search(r"\{[\s\S]+\}", cleaned)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                raise ValueError(
                    "Khong the parse JSON tu response AI"
                ) from exc
        else:
            raise ValueError("Khong tim thay JSON trong response AI") from exc

    # Validate và xây dựng AnalysisResult
    checklist_raw = data.get("checklist", [])
    checklist = []
    for item in checklist_raw:
        if isinstance(item, dict):
            # Lấy điểm trừ của tiêu chí (nếu AI cung cấp, hoặc tự trích xuất từ note/item)
            deduction_val = item.get("deduction")
            try:
                deduction = int(deduction_val) if deduction_val is not None else 0
            except (ValueError, TypeError):
                deduction = 0

            # Lấy tầm quan trọng (importance)
            importance = str(item.get("importance", "minor")).strip().lower()
            if importance not in ("core", "minor"):
                if deduction >= 30:
                    importance = "core"
                else:
                    importance = "minor"

            # Nếu deduction chưa được thiết lập, dùng regex tìm số điểm bị trừ trong note hoặc item
            if deduction <= 0 and not bool(item.get("met", False)):
                text_to_search = f"{item.get('note', '')} {item.get('item', '')}"
                match = re.search(r"[Tt]rừ\s+(\d+)", text_to_search)
                if match:
                    try:
                        deduction = int(match.group(1))
                    except (ValueError, TypeError):
                        pass

            # Dự phòng mặc định nếu là tiêu chí thất bại mà điểm trừ vẫn là 0
            if not bool(item.get("met", False)) and deduction <= 0:
                deduction = 20

            # Đồng bộ điểm trừ tối thiểu dựa trên độ quan trọng (kể cả khi met là True để phân loại core/minor chính xác)
            if importance == "core":
                if deduction < 30:
                    deduction = 30
            else:
                if not bool(item.get("met", False)) and deduction < 10:
                    deduction = 10

            checklist.append(
                ChecklistItem(
                    item=str(item.get("item", "Tiêu chí không rõ")),
                    met=bool(item.get("met", False)),
                    note=item.get("note") or None,
                    deduction=max(0, deduction),
                    importance=importance,
                )
            )

    # Lọc bỏ các tiêu chí hình thức do AI tự bịa ra nếu yêu cầu nhiệm vụ không đề cập
    task_requirements_text = f"{task_name} {task_description}".lower()
    sanitized_checklist = []
    for it in checklist:
        it_text_lower = it.item.lower()

        # 1. Kiểm tra tiêu chí về tên file
        if ("tên file" in it_text_lower or "tên tệp" in it_text_lower) and ("tên file" not in task_requirements_text and "tên tệp" not in task_requirements_text):
            logger.info("Dropping hallucinated checklist item (file name): %s", it.item)
            continue

        # 2. Kiểm tra tiêu chí về định dạng file
        if ("định dạng" in it_text_lower or "loại file" in it_text_lower) and ("định dạng" not in task_requirements_text and "loại file" not in task_requirements_text and "excel" not in task_requirements_text and "pdf" not in task_requirements_text and "word" not in task_requirements_text):
            logger.info("Dropping hallucinated checklist item (file format): %s", it.item)
            continue

        # 3. Kiểm tra tiêu chí về số trang / số sheets
        if ("số trang" in it_text_lower or "số lượng trang" in it_text_lower or "số sheet" in it_text_lower) and ("số trang" not in task_requirements_text and "số lượng trang" not in task_requirements_text and "số sheet" not in task_requirements_text):
            logger.info("Dropping hallucinated checklist item (page count): %s", it.item)
            continue

        sanitized_checklist.append(it)

    checklist = sanitized_checklist

    # Đảm bảo luôn có ít nhất 1 checklist item
    if not checklist:
        checklist = [ChecklistItem(item="Nội dung phù hợp với nhiệm vụ", met=True, deduction=0, importance="minor")]

    # Tính toán compatibility_score lập trình ở Backend
    total_deductions = sum(it.deduction for it in checklist if not it.met)
    all_failed = all(not it.met for it in checklist)

    # Tiêu chí cốt lõi là các tiêu chí có importance == "core" hoặc có điểm trừ từ 30 trở lên
    core_items = [it for it in checklist if it.importance == "core" or it.deduction >= 30]
    all_core_failed = all(not it.met for it in core_items) if core_items else False

    if all_failed or all_core_failed:
        score = 0
    else:
        score = max(0, 100 - total_deductions)

    ai_comment = str(data.get("ai_comment", "Không có nhận xét."))

    if score == 100:
        ai_comment = "Tài liệu đạt 100 điểm. Minh chứng hoàn hảo, đáp ứng đầy đủ tất cả các tiêu chí và yêu cầu của nhiệm vụ."
    else:
        # Đồng bộ hóa điểm số trong nhận xét của AI để tránh mâu thuẫn số liệu
        ai_comment = re.sub(
            r'(đạt|được|đạt được)\s+\d+\s*(điểm|%)',
            f'\\1 {score} \\2',
            ai_comment,
            flags=re.IGNORECASE
        )

        # Nếu chỉ có duy nhất một tiêu chí bị đánh giá met=False, đồng bộ cả số điểm bị trừ trong bình luận
        failed_items = [it for it in checklist if not it.met]
        if len(failed_items) == 1:
            failed_item = failed_items[0]
            ai_comment = re.sub(
                r'(trừ|bị trừ|khấu trừ)\s+\d+\s*(điểm|%)',
                f'\\1 {failed_item.deduction} \\2',
                ai_comment,
                flags=re.IGNORECASE
            )

    return AnalysisResult(
        compatibility_score=score,
        checklist=checklist,
        ai_comment=ai_comment,
        strengths=list(data.get("strengths", [])),
        weaknesses=list(data.get("weaknesses", [])),
        extracted_text_length=extracted_len,
        model_used=model_used,
        analyzed_at=datetime.utcnow(),
    )


# ══════════════════════════════════════════════════════════════════════
# Fallback khi AI lỗi
# ══════════════════════════════════════════════════════════════════════

def _fallback_result(error_msg: str) -> AnalysisResult:
    """Trả về kết quả fallback khi API lỗi."""
    return AnalysisResult(
        compatibility_score=0,
        checklist=[
            ChecklistItem(
                item="Phân tích AI",
                met=False,
                note="Lỗi trong quá trình phân tích",
            )
        ],
        ai_comment=f"Không thể phân tích tài liệu do lỗi kỹ thuật: {error_msg[:200]}",
        strengths=[],
        weaknesses=["Hệ thống gặp lỗi khi phân tích, vui lòng thử lại"],
        extracted_text_length=0,
        model_used="none",
        analyzed_at=datetime.utcnow(),
    )


# ══════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════

async def analyze(
    *,
    # File info
    filename: str,
    file_type: str,         # 'pdf' | 'word' | 'excel' | 'image'
    extracted_text: str,
    image_b64: str,
    page_count: int,
    is_image: bool,
    # Task info
    task_name: str,
    task_description: str,
    task_deadline: str,
    task_weight: int,
    uploader_name: str,
    department: str,
) -> AnalysisResult:
    """
    Phân tích minh chứng bằng OpenRouter AI.

    Tự động:
      - Chọn TEXT_MODEL cho file text
      - Chọn VISION_MODEL cho file ảnh (gửi kèm image base64)

    Returns:
        AnalysisResult với điểm số, checklist, nhận xét.
    """

    try:
        # Xác định model sử dụng
        if settings.groq_api_key:
            model = "llama-3.2-11b-vision-preview" if (is_image and image_b64) else "llama-3.3-70b-versatile"
        elif settings.gemini_api_key:
            model = "gemini-2.5-flash"
        else:
            model = settings.vision_model if (is_image and image_b64) else settings.text_model

        if is_image and image_b64:
            # ── Vision branch ─────────────────────────────────────────
            user_text = _USER_PROMPT_TEMPLATE.format(
                task_name=task_name,
                task_description=task_description or "(không có mô tả)",
                task_deadline=task_deadline or "(chưa đặt)",
                task_weight=task_weight,
                uploader_name=uploader_name,
                department=department or "(chưa rõ)",
                filename=filename,
                file_type="HÌNH ẢNH",
                page_count=page_count,
                content_section="[Hình ảnh đính kèm bên dưới – hãy phân tích nội dung từ ảnh]",
            )

            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_b64},
                        },
                    ],
                },
            ]

            logger.info("Calling vision model %s for image file: %s", model, filename)
            raw = await _call_ai_api(model=model, messages=messages)

        else:
            # ── Text branch ───────────────────────────────────────────
            user_text = _build_text_prompt(
                task_name=task_name,
                task_description=task_description,
                task_deadline=task_deadline,
                task_weight=task_weight,
                uploader_name=uploader_name,
                department=department,
                filename=filename,
                file_type=file_type,
                page_count=page_count,
                extracted_text=extracted_text,
            )

            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ]

            logger.info("Calling text model %s for file: %s", model, filename)
            raw = await _call_ai_api(model=model, messages=messages)

        # Parse kết quả
        result = _parse_ai_response(
            raw=raw,
            model_used=model,
            extracted_len=len(extracted_text),
            task_name=task_name,
            task_description=task_description,
        )
        logger.info(
            "Analysis done for %s: score=%d, checklist=%d items",
            filename, result.compatibility_score, len(result.checklist),
        )
        return result

    except httpx.HTTPStatusError as exc:
        if settings.groq_api_key:
            provider = "Groq"
        elif settings.gemini_api_key:
            provider = "Gemini"
        else:
            provider = "OpenRouter"
        err = f"{provider} HTTP {exc.response.status_code}"
        logger.error("%s HTTP error %s: %s", provider, exc.response.status_code,
                     _safe(exc.response.text, 200))
        return _fallback_result(err)

    except httpx.RequestError as exc:
        if settings.groq_api_key:
            provider = "Groq"
        elif settings.gemini_api_key:
            provider = "Gemini"
        else:
            provider = "OpenRouter"
        err = f"Loi ket noi den {provider}: {type(exc).__name__}"
        logger.error("Request error: %s", _safe(exc))
        return _fallback_result(err)

    except UnicodeEncodeError as exc:
        # ASCII encode error khi xu ly filename/content tieng Viet tren Windows
        err = f"Loi encoding (Unicode): {exc.reason} tai vi tri {exc.start}"
        logger.error("UnicodeEncodeError in ai_analyzer: %s", _safe(exc))
        return _fallback_result(err)

    except ValueError as exc:
        err = f"Loi parse ket qua AI: {_safe(exc)}"
        logger.error("ValueError in ai_analyzer: %s", _safe(exc))
        return _fallback_result(err)

    except Exception as exc:  # noqa: BLE001
        err = f"Loi khong xac dinh: {type(exc).__name__}: {_safe(exc)}"
        logger.exception("Unexpected error in ai_analyzer")
        return _fallback_result(err)
