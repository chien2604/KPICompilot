import json
import logging
from abc import ABC, abstractmethod

from core.config import get_settings

LOGGER = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Define the text-completion interface used by the AI layer."""

    @abstractmethod
    def complete(
        self, prompt: str, system_prompt: str | None = None, expect_json: bool = False
    ) -> str:
        """Complete a prompt and optionally return a JSON object string."""

        raise NotImplementedError


class UnavailableLLMClient(BaseLLMClient):
    """Return explicit unavailable responses without fabricating business data."""

    def complete(
        self, prompt: str, system_prompt: str | None = None, expect_json: bool = False
    ) -> str:
        """Return a deterministic control response when no LLM provider is configured."""

        if "Tóm tắt câu hỏi dưới đây thành tiêu đề ngắn" in prompt:
            question = prompt.split("Câu hỏi:", 1)[-1].strip()
            words = question.replace("?", "").replace(".", "").split()
            return " ".join(words[:8]) or "Hội thoại KPI"
        if expect_json or _expects_json(prompt, system_prompt):
            return json.dumps({}, ensure_ascii=False)
        return "Dịch vụ AI chưa được cấu hình hoặc đang không khả dụng. Hệ thống không tạo nội dung thay thế để tránh sai lệch dữ liệu."


class OpenAILLMClient(BaseLLMClient):
    """Call an OpenAI-compatible chat completion provider."""

    def __init__(self) -> None:
        """Initialize the configured OpenAI-compatible client."""

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
            timeout=120.0,  # Tăng timeout của LLM lên 120 giây (2 phút)
        )

    def complete(
        self, prompt: str, system_prompt: str | None = None, expect_json: bool = False
    ) -> str:
        """Send one completion request and return its text content."""

        kwargs = {}
        if expect_json or _expects_json(prompt, system_prompt):
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt or "Bạn là trợ lý AI trả lời tiếng Việt.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            seed=42,
            **kwargs,
        )
        return response.choices[0].message.content or ""


def _expects_json(prompt: str, system_prompt: str | None) -> bool:
    """Detect prompts that explicitly require a JSON response."""

    content = (prompt + " " + (system_prompt or "")).lower()
    # Tránh tự động nhận diện nhầm khi prompt chứa dữ liệu JSON dumps hoặc cấm hiển thị JSON
    if (
        "dữ liệu hệ thống" in content
        or "graph rag" in content
        or "không hiển thị json" in content
    ):
        return False
    return any(
        x in content
        for x in [
            "trả về json",
            "định dạng json",
            "cấu trúc json",
            "format: json",
            "json_object",
            "return json",
        ]
    )


def get_llm_client() -> BaseLLMClient:
    """Build the configured LLM client or an explicit unavailable client."""

    settings = get_settings()
    if settings.openai_api_key:
        try:
            return OpenAILLMClient()
        except Exception as error:
            LOGGER.warning("Không thể khởi tạo LLM provider: %s", error)
    return UnavailableLLMClient()
