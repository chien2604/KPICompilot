import json
from pathlib import Path

from ai_layer.llm_client import BaseLLMClient, get_llm_client


PROMPT = Path(__file__).parent / "prompts" / "evidence_analyzer_prompt.txt"


class EvidenceAnalyzer:
    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()

    def analyze(self, task_title: str, task_description: str | None, evidence_text: str) -> dict:
        prompt = (
            f"{PROMPT.read_text(encoding='utf-8')}\n\n"
            f"Nhiệm vụ: {task_title}\n"
            f"Mô tả: {task_description or ''}\n"
            f"Nội dung minh chứng:\n{evidence_text[:6000]}"
        )
        try:
            raw = self.llm.complete(prompt)
            data = json.loads(raw)
        except Exception:
            data = {
                "relevance_score": 70,
                "summary": "Minh chứng đã được đọc nhưng AI chưa trả về JSON hợp lệ.",
                "checklist": [],
                "missing_points": ["Cần rà soát thủ công nội dung minh chứng."],
                "related_kpi_criteria": [],
                "recommendation": "Tạm chấp nhận ở mức trung bình cho PoC.",
            }
        return data
