import json
from pathlib import Path

from ai_layer.llm_client import BaseLLMClient, get_llm_client


PROMPT = Path(__file__).parent / "prompts" / "report_generator_prompt.txt"


class ReportGenerator:
    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()

    def generate(self, data: dict) -> str:
        prompt = f"{PROMPT.read_text(encoding='utf-8')}\n\nDữ liệu:\n{json.dumps(data, ensure_ascii=False, indent=2)}"
        try:
            return self.llm.complete(prompt)
        except Exception:
            return "<h2>Báo cáo giao ban</h2><p>Chưa sinh được báo cáo AI, vui lòng kiểm tra cấu hình LLM.</p>"
