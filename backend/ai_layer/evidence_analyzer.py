import difflib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_layer.llm_client import BaseLLMClient, get_llm_client

logger = logging.getLogger(__name__)

_PROMPTS = Path(__file__).parent / "prompts"

# ── Load prompts từ file chung (ai_layer/prompts/) ──────────────────────────
_P1_SYSTEM = (_PROMPTS / "evidence_phase1_system.txt").read_text(encoding="utf-8")
_P1_USER   = (_PROMPTS / "evidence_phase1_user.txt").read_text(encoding="utf-8")
_P2_SYSTEM = (_PROMPTS / "evidence_phase2_system.txt").read_text(encoding="utf-8")
_P2_USER   = (_PROMPTS / "evidence_phase2_user.txt").read_text(encoding="utf-8")


def _extract_requirements(task_description: str) -> list[str]:
    text = (task_description or "").strip()
    if not text:
        return []
    numbered = re.split(r'(?<!\d)(?:\d+[.)]\s+|\(\d+\)\s+)', text)
    numbered = [r.strip().rstrip(';,') for r in numbered if r.strip()]
    if len(numbered) >= 2:
        return numbered
    bulleted = re.split(r'(?:^|\n)\s*[-*•]\s+', text)
    bulleted = [r.strip().rstrip(';,') for r in bulleted if r.strip()]
    if len(bulleted) >= 2:
        return bulleted
    by_semicolon = [r.strip() for r in text.split(';') if r.strip()]
    if len(by_semicolon) >= 2:
        return by_semicolon
    VN_REQ_STARTERS = r'có |đạt |bao gồm |phải |cần |gồm |kèm |đính kèm |thể hiện |đảm bảo |xác nhận |chứng minh |ghi rõ |nêu rõ '
    by_comma = re.split(rf',\s*(?={VN_REQ_STARTERS})', text, flags=re.IGNORECASE)
    by_comma = [r.strip().rstrip(',') for r in by_comma if r.strip()]
    if len(by_comma) >= 2:
        return by_comma
    by_newline = [r.strip() for r in text.splitlines() if r.strip()]
    if len(by_newline) >= 2:
        return by_newline
    return [text]


def _parse_ai_response(raw: str, task_name: str = "", requirements: list[str] = None) -> dict:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().strip("`").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]+\}", cleaned)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                raise ValueError("Không thể parse JSON từ response AI")
        else:
            raise ValueError("Không tìm thấy JSON trong response AI")

    checklist_raw = data.get("checklist", [])
    checklist = []
    for item in checklist_raw:
        if isinstance(item, dict):
            deduction_val = item.get("deduction")
            try:
                deduction = int(deduction_val) if deduction_val is not None else 0
            except (ValueError, TypeError):
                deduction = 0

            importance = str(item.get("importance", "minor")).strip().lower()
            if importance not in ("core", "minor"):
                importance = "core" if deduction >= 30 else "minor"

            if deduction <= 0 and not bool(item.get("met", False)):
                match = re.search(r"[Tt]rừ\s+(\d+)", f"{item.get('note', '')} {item.get('item', '')}")
                if match:
                    try:
                        deduction = int(match.group(1))
                    except (ValueError, TypeError):
                        pass

            if deduction <= 0:
                deduction = 30 if importance == "core" else 10

            checklist.append({
                "item": str(item.get("item", "Tiêu chí không rõ")),
                "met": bool(item.get("met", False)),
                "note": item.get("note") or "",
                "deduction": max(0, deduction),
                "importance": importance,
            })
    req_pool = list(requirements) if requirements else []
    if task_name and task_name not in req_pool:
        req_pool.insert(0, task_name)

    def _find_matching_requirement(item_name: str, pool: list[str]) -> str | None:
        item_clean = item_name.strip().lower()
        _STOP = {"tài", "liệu", "có", "và", "là", "của", "trong", "về", "cho", "với", "được", "theo", "đầy", "đủ", "thông", "tin", "các", "một", "khi", "hoặc", "nếu", "này", "đúng", "hợp", "lệ", "phù", "hợp", "rõ", "ràng", "đã", "chưa", "bị", "được", "phải", "cần", "nên", "không", "kết", "quả"}
        def _kw(text: str) -> set[str]:
            return {t for t in re.findall(r'\w{3,}', text.lower()) if t not in _STOP}
            
        item_keywords = _kw(item_clean)
        best_ratio = 0.0
        best_req = None
        for req in pool:
            req_clean = req.strip().lower()
            if item_clean == req_clean:
                return req
            if req_clean in item_clean or item_clean in req_clean:
                ratio = 0.85 + 0.1 * (min(len(req_clean), len(item_clean)) / max(len(req_clean), len(item_clean), 1))
            else:
                ratio = difflib.SequenceMatcher(None, item_clean, req_clean).ratio()
            
            # Boost ratio if they share keywords
            req_keywords = _kw(req_clean)
            shared_keywords = item_keywords & req_keywords
            if shared_keywords:
                ratio += min(0.3, 0.15 * len(shared_keywords))
                
            if ratio > best_ratio:
                best_ratio = ratio
                best_req = req
        if best_ratio >= 0.45:
            return best_req
        return None

    sanitized_checklist = []
    for it in checklist:
        matching_req = _find_matching_requirement(it["item"], req_pool)
        if matching_req:
            it["item"] = matching_req
            sanitized_checklist.append(it)

    if not sanitized_checklist:
        sanitized_checklist = [{"item": "Nội dung phù hợp với nhiệm vụ", "met": True, "note": "", "deduction": 0, "importance": "minor"}]

    # Proportionally scale deductions if total raw sum exceeds 100
    total_raw_deductions = sum(it["deduction"] for it in sanitized_checklist)
    if total_raw_deductions > 100:
        scaled_sum = 0
        for it in sanitized_checklist:
            scaled = (it["deduction"] / total_raw_deductions) * 100
            it["deduction"] = max(1, int(round(scaled)))
            scaled_sum += it["deduction"]
            
        diff = 100 - scaled_sum
        if diff != 0 and sanitized_checklist:
            largest_item = max(sanitized_checklist, key=lambda x: x["deduction"])
            largest_item["deduction"] = max(1, largest_item["deduction"] + diff)

    total_deductions = sum(it["deduction"] for it in sanitized_checklist if not it["met"])
    all_failed = all(not it["met"] for it in sanitized_checklist)
    core_items = [it for it in sanitized_checklist if it["importance"] == "core" or it["deduction"] >= 30]
    all_core_failed = all(not it["met"] for it in core_items) if core_items else False

    score = 0 if (all_failed or all_core_failed) else max(0, 100 - total_deductions)

    ai_comment = str(data.get("ai_comment", "Không có nhận xét."))
    if score == 100:
        ai_comment = "Tài liệu đạt 100 điểm. Minh chứng hoàn hảo, đáp ứng đầy đủ tất cả các tiêu chí và yêu cầu của nhiệm vụ."
    else:
        ai_comment = re.sub(r'(đạt|được|đạt được)\s+\d+\s*(điểm|%)', f'\\1 {score} \\2', ai_comment, flags=re.IGNORECASE)
        failed_items = [it for it in sanitized_checklist if not it["met"]]
        if len(failed_items) == 1:
            ai_comment = re.sub(r'(trừ|bị trừ|khấu trừ)\s+\d+\s*(điểm|%)', f'\\1 {failed_items[0]["deduction"]} \\2', ai_comment, flags=re.IGNORECASE)

    return {
        "relevance_score": score,
        "summary": ai_comment,
        "checklist": sanitized_checklist,
        "strengths": list(data.get("strengths", [])),
        "weaknesses": list(data.get("weaknesses", []))
    }


class EvidenceAnalyzer:
    def __init__(self, llm: BaseLLMClient | None = None) -> None:
        self.llm = llm or get_llm_client()

    def _fallback_result(self, error_msg: str) -> dict:
        return {
            "relevance_score": 0,
            "summary": f"Không thể phân tích tài liệu do lỗi kỹ thuật: {error_msg[:200]}",
            "checklist": [{
                "item": "Phân tích AI",
                "met": False,
                "note": "Lỗi trong quá trình phân tích",
                "deduction": 100,
                "importance": "core"
            }],
            "strengths": [],
            "weaknesses": ["Hệ thống gặp lỗi khi phân tích, vui lòng thử lại"]
        }

    def analyze(
        self, 
        task_title: str, 
        task_description: str | None, 
        evidence_text: str,
        uploader_name: str = "(không rõ)",
        department: str = "(không rõ)",
        task_deadline: str = "(chưa đặt)",
        filename: str = "(không rõ)",
        file_type: str = "(không rõ)",
    ) -> dict:
        try:
            logger.info("[Phase 1] Building checklist from requirements")
            p1_user = _P1_USER.format(task_name=task_title, task_description=task_description or "(không có mô tả)")
            p1_raw = self.llm.complete(prompt=p1_user, system_prompt=_P1_SYSTEM, expect_json=True)
            
            p1_items = []
            try:
                p1_cleaned = re.sub(r"```(?:json)?\s*", "", p1_raw).strip().strip("`").strip()
                p1_data = json.loads(p1_cleaned)
                p1_items = p1_data.get("checklist", [])
            except Exception:
                pass

            requirements = _extract_requirements(task_description or task_title)

            def _is_valid_p1_item(item_name: str, pool: list[str]) -> bool:
                item_clean = item_name.strip().lower()
                for req in pool:
                    req_clean = req.strip().lower()
                    if req_clean in item_clean or item_clean in req_clean:
                        return True
                    ratio = difflib.SequenceMatcher(None, item_clean, req_clean).ratio()
                    if ratio >= 0.45:
                        return True
                return False

            if p1_items and requirements:
                p1_items = [item for item in p1_items if _is_valid_p1_item(item.get("item", ""), requirements)]

            if not p1_items:
                p1_items = [{"item": req, "importance": "core", "deduction": 30} for req in requirements]

            checklist_section = "\n".join(
                f"({i+1}) [{item.get('importance','core').upper()}] {item.get('item','')} "
                f"(trừ {item.get('deduction',30)} điểm nếu không đạt)"
                for i, item in enumerate(p1_items)
            )

            logger.info("[Phase 2] Verifying checklist against document")
            trimmed_text = evidence_text[:32000]
            if len(evidence_text) > 32000:
                trimmed_text += "\n\n[... nội dung bị cắt bớt ...]"

            p2_user = _P2_USER.format(
                checklist_section=checklist_section,
                uploader_name=uploader_name,
                department=department,
                task_deadline=task_deadline,
                filename=filename,
                file_type=file_type.upper(),
                content_section=f"Nội dung trích xuất:\n{trimmed_text}",
            )
            raw = self.llm.complete(prompt=p2_user, system_prompt=_P2_SYSTEM, expect_json=True)
            
            return _parse_ai_response(
                raw=raw, 
                task_name=task_title, 
                requirements=[item.get("item", "") for item in p1_items]
            )

        except Exception as exc:
            logger.exception("Error in EvidenceAnalyzer")
            return self._fallback_result(str(exc))