import json
from abc import ABC, abstractmethod

from core.config import get_settings


class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt or "Bạn là trợ lý AI trả lời tiếng Việt."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


def get_llm_client() -> BaseLLMClient:
    if get_settings().openai_api_key:
        try:
            return OpenAILLMClient()
        except Exception:
            return MockLLMClient()
    return MockLLMClient()
