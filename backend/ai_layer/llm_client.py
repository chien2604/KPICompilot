import json
from abc import ABC, abstractmethod

from core.config import get_settings


class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        if "Tóm tắt câu hỏi dưới đây thành tiêu đề ngắn" in prompt:
            question = prompt.split("Câu hỏi:", 1)[-1].strip()
            words = question.replace("?", "").replace(".", "").split()
            return " ".join(words[:8]) or "Hội thoại KPI"
        if "Tóm tắt hội thoại" in prompt or "summary" in prompt.lower():
            return "Người dùng đang trao đổi về KPI, tiến độ nhiệm vụ và các rủi ro cần lãnh đạo theo dõi."
        if "relevance_score" in prompt:
            return json.dumps(
                {
                    "relevance_score": 82,
                    "summary": "Minh chứng phù hợp với nhiệm vụ, thể hiện kết quả xử lý và có căn cứ tiến độ.",
                    "checklist": ["Có nội dung liên quan nhiệm vụ", "Có dấu hiệu hoàn thành đầu việc chính"],
                    "missing_points": ["Nên bổ sung ngày ban hành hoặc người phê duyệt nếu có"],
                    "related_kpi_criteria": ["Hiệu quả thực hiện nhiệm vụ"],
                    "recommendation": "Chấp nhận minh chứng cho đánh giá KPI PoC.",
                },
                ensure_ascii=False,
            )
        if "báo cáo giao ban" in prompt.lower():
            return "<h2>Báo cáo giao ban</h2><p>Tình hình chung ổn định, cần tập trung xử lý các nhiệm vụ quá hạn và nhóm cán bộ có KPI rủi ro.</p>"
        return "Dựa trên dữ liệu hiện có, hệ thống ghi nhận một số nhiệm vụ chậm tiến độ và nhóm KPI rủi ro cần lãnh đạo theo dõi. Đây là phản hồi mock để demo khi chưa cấu hình LLM thật."


class OpenAILLMClient(BaseLLMClient):
    def __init__(self) -> None:
        from openai import OpenAI

        settings = get_settings()
        self.model = settings.openai_model
        default_headers = {}
        if settings.openai_base_url and "openrouter.ai" in settings.openai_base_url:
            default_headers = {
                "HTTP-Referer": settings.openrouter_site_url,
                "X-Title": settings.openrouter_app_name,
            }
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            default_headers=default_headers or None,
        )

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        import hashlib
        cache_key = hashlib.md5(f"{prompt}||{system_prompt}".encode("utf-8")).hexdigest()
        global _LLM_CACHE
        if "_LLM_CACHE" not in globals():
            _LLM_CACHE = {}
        if cache_key in _LLM_CACHE:
            return _LLM_CACHE[cache_key]

        kwargs = {}
        if _expects_json(prompt, system_prompt):
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt or "Bạn là trợ lý AI trả lời tiếng Việt."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            seed=42,
            **kwargs,
        )
        result = response.choices[0].message.content or ""
        _LLM_CACHE[cache_key] = result
        return result

def _expects_json(prompt: str, system_prompt: str | None) -> bool:
    content = (prompt + " " + (system_prompt or "")).lower()
    return "json" in content


def get_llm_client() -> BaseLLMClient:
    settings = get_settings()
    if settings.openai_api_key:
        try:
            return OpenAILLMClient()
        except Exception:
            pass
    return MockLLMClient()