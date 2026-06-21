"""
ai_layer/report_generator.py – Sinh báo cáo giao ban dưới dạng HTML fragment bằng LLM.

THIẾT KẾ: Đây là nguồn dữ liệu CHÍNH cho báo cáo (không qua JSON blocks abstraction).
LLM được yêu cầu trả về HTML fragment đầy đủ (kèm tiêu ngữ hành chính, các mục theo
report_generator_prompt.txt) và HTML đó được lưu trực tiếp vào Report.content.

Có retry 1 lần nếu output của LLM không hợp lệ (ví dụ: bị bọc trong ```html, thiếu
tiêu ngữ bắt buộc, hoặc rỗng), để tránh rơi vào fallback cứng khi LLM thật ra có khả
năng tạo đúng nhưng output lần đầu sai format do model tự ý thêm code fence/giải thích.

Mọi lần fallback đều được log WARNING rõ lý do, kèm cờ "_source" gắn vào kết quả
trả về để bên gọi (ReportService) biết và lưu vào summary_json, giúp debug từ DB/API
mà không cần đọc log server.
"""
import logging
import re
from pathlib import Path

from ai_layer.llm_client import BaseLLMClient, get_llm_client

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "report_generator_prompt.txt"

_RETRY_SUFFIX = """

LƯU Ý: Lần trả lời trước của bạn KHÔNG đúng yêu cầu (lỗi: {error}).
Lần này PHẢI tuân thủ NGHIÊM NGẶT các quy tắc:
- CHỈ xuất HTML fragment thuần, KHÔNG bọc trong ```html hoặc bất kỳ markdown code fence nào.
- KHÔNG thêm lời giải thích, lời chào, hoặc ghi chú nào trước/sau HTML.
- PHẢI có đúng 2 dòng tiêu ngữ ở đầu, nguyên vẹn như yêu cầu gốc.
- PHẢI có đủ 5 mục: "1. Tình hình chung", "2. Điểm sáng", "3. Nhiệm vụ chậm",
  "4. Cá nhân/phòng ban rủi ro", "5. Kiến nghị"."""

_REQUIRED_HEADINGS = [
    "1. Tình hình chung",
    "2. Điểm sáng",
    "3. Nhiệm vụ chậm",
    "4. Cá nhân/phòng ban rủi ro",
    "5. Kiến nghị",
]

_TIEU_NGU_LINE_1 = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
_TIEU_NGU_LINE_2 = "Độc lập - Tự do - Hạnh phúc"


def _clean_html(raw: str) -> str:
    """Loại bỏ code fence markdown nếu LLM lỡ bọc HTML trong ```html ... ```."""
    cleaned = (raw or "").strip()
    cleaned = re.sub(r"^```(?:html)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _validate_html(html: str) -> str | None:
    """Kiểm tra HTML có đáp ứng các ràng buộc BẮT BUỘC của prompt hay không.

    Trả về None nếu hợp lệ, hoặc chuỗi mô tả lý do không hợp lệ để dùng cho retry/log.
    Đây KHÔNG phải kiểm tra ngữ nghĩa đầy đủ (không thể verify số liệu khớp JSON ở đây),
    chỉ kiểm tra các ràng buộc CẤU TRÚC rõ ràng: có tiêu ngữ, có đủ heading, không rỗng,
    không còn dính code fence.
    """
    if not html or len(html.strip()) < 50:
        return "HTML quá ngắn hoặc rỗng"

    if "```" in html:
        return "HTML vẫn còn dính markdown code fence (```)"

    if _TIEU_NGU_LINE_1 not in html:
        return f"Thiếu tiêu ngữ '{_TIEU_NGU_LINE_1}'"

    if _TIEU_NGU_LINE_2 not in html:
        return f"Thiếu tiêu ngữ '{_TIEU_NGU_LINE_2}'"

    missing_headings = [h for h in _REQUIRED_HEADINGS if h not in html]
    if missing_headings:
        return f"Thiếu các mục bắt buộc: {', '.join(missing_headings)}"

    return None


class ReportGenerator:
    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()
        self._prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    def generate(self, data: dict) -> dict:
        """Sinh báo cáo HTML từ dữ liệu thống kê.

        Trả về dict {"html": str, "_source": "llm" | "llm_retry" | "fallback"}.
        "_source" giúp biết ngay báo cáo có phải AI sinh thật hay không, không cần đọc log.
        """
        import json as _json

        prompt = f"{self._prompt_template}\n\nDữ liệu:\n{_json.dumps(data, ensure_ascii=False, indent=2)}"
        llm_class_name = type(self.llm).__name__
        logger.info("[ReportGenerator] Gọi LLM (%s) để sinh báo cáo HTML", llm_class_name)

        html, error = self._call_and_validate(prompt)
        if html:
            logger.info("[ReportGenerator] LLM sinh báo cáo HTML thành công ở lần gọi đầu (%d ký tự)", len(html))
            return {"html": html, "_source": "llm"}

        logger.warning(
            "[ReportGenerator] Lần gọi LLM đầu KHÔNG đạt yêu cầu (lý do: %s). Đang retry lần 2...", error
        )
        retry_prompt = prompt + _RETRY_SUFFIX.format(error=error)
        html, second_error = self._call_and_validate(retry_prompt)
        if html:
            logger.info("[ReportGenerator] LLM sinh báo cáo HTML thành công ở lần retry (%d ký tự)", len(html))
            return {"html": html, "_source": "llm_retry"}

        logger.warning(
            "[ReportGenerator] Cả 2 lần gọi LLM (%s) đều KHÔNG đạt yêu cầu (lần 1: %s | lần 2: %s). "
            "DÙNG FALLBACK ĐƠN GIẢN. Kiểm tra API key/model/network nếu báo cáo trông không đúng prompt.",
            llm_class_name, error, second_error,
        )
        return {"html": self._fallback_html(second_error), "_source": "fallback"}

    def _call_and_validate(self, prompt: str) -> tuple[str | None, str | None]:
        try:
            raw = self.llm.complete(prompt)
        except Exception as exc:
            logger.exception("[ReportGenerator] LLM client raise exception khi gọi complete()")
            return None, f"LLM call exception: {exc}"

        logger.debug("[ReportGenerator] Raw LLM response (first 500 chars): %s", raw[:500] if raw else "(rỗng)")
        cleaned = _clean_html(raw)
        error = _validate_html(cleaned)
        if error:
            return None, error
        return cleaned, None

    def _fallback_html(self, reason: str | None) -> str:
        return (
            "<p style='text-align:center;'><strong>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</strong></p>"
            "<p style='text-align:center;'><strong>Độc lập - Tự do - Hạnh phúc</strong></p>"
            "<h2 style='text-align:center;'>BÁO CÁO GIAO BAN</h2>"
            "<p><em>Không sinh được báo cáo từ AI sau 2 lần thử"
            f"{f' (lý do: {reason})' if reason else ''}. "
            "Vui lòng kiểm tra cấu hình LLM (GROQ_API_KEY/OPENAI_API_KEY) hoặc thử sinh lại báo cáo.</em></p>"
        )