import json
from pathlib import Path

from ai_layer.llm_client import BaseLLMClient, get_llm_client


PROMPT = Path(__file__).parent / "prompts" / "kpi_explainer_prompt.txt"


class KPIExplainer:
    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()

    def explain(self, payload: dict) -> str:
        prompt = f"{PROMPT.read_text(encoding='utf-8')}\n\nDữ liệu KPI:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        try:
            return self.llm.complete(prompt)
        except Exception:
            return "Điểm KPI được tính từ Rule Engine dựa trên tiến độ nhiệm vụ, hạn xử lý và minh chứng liên quan."
