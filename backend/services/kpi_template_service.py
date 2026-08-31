"""Synchronize official KPI templates and common criteria."""

from collections.abc import Iterable

from core.organization import POSITION_TEMPLATES
from db.models.kpi import DocumentTypeRule, KPICriterion, KPIScore, KPITemplate
from sqlalchemy.orm import Session

DOCUMENT_TYPE_RULES = (
    ("A", "Nhóm A", "Sản phẩm chiến lược hoặc hồ sơ tác động lớn."),
    ("B", "Nhóm B", "Kế hoạch, báo cáo, chuyên đề hoặc văn bản tham mưu."),
    ("C", "Nhóm C", "Hồ sơ hành chính hoặc báo cáo, phối hợp định kỳ."),
    ("D", "Nhóm D", "Biên bản, trao đổi hoặc thông tin nghiệp vụ ngắn."),
)


class KPITemplateService:
    """Replace legacy templates with Decision 283 common criteria."""

    def __init__(self, database_session: Session) -> None:
        """Store the database session used for template synchronization."""

        self.database_session = database_session

    def replace_templates(self, common_criteria: Iterable) -> None:
        """Create eligible role templates and copy the official common criteria."""

        self.database_session.query(KPIScore).delete()
        self.database_session.query(KPICriterion).delete()
        self.database_session.query(KPITemplate).delete()
        criteria = list(common_criteria)
        for position_template in POSITION_TEMPLATES:
            template = KPITemplate(
                code=position_template.code,
                name=position_template.name,
                target_role=position_template.organization_role,
                total_score=100,
            )
            self.database_session.add(template)
            self.database_session.flush()
            if position_template.code == "CHUA_THUOC_PHAM_VI_KPI":
                continue
            for criterion in criteria:
                self.database_session.add(
                    KPICriterion(
                        template_id=template.id,
                        group_code=criterion.group_code,
                        group_name=criterion.group_name,
                        criterion_code=criterion.criterion_code,
                        criterion_name=criterion.criterion_name,
                        description="Tiêu chí chung theo Quyết định 283/QĐ-UBND.",
                        calculation_rule_text=(
                            "Điểm do người có thẩm quyền đánh giá; không do LLM tính."
                        ),
                        max_score=criterion.max_score,
                        sort_order=criterion.sort_order,
                    )
                )
        self._replace_document_type_rules()
        self.database_session.flush()

    def _replace_document_type_rules(self) -> None:
        """Retain document groups as metadata, not as an unofficial multiplier."""

        self.database_session.query(DocumentTypeRule).delete()
        for code, name, description in DOCUMENT_TYPE_RULES:
            self.database_session.add(
                DocumentTypeRule(
                    code=code,
                    name=name,
                    description=description,
                    scoring_rule_text=(
                        "Không trực tiếp nhân điểm KPI theo Nghị định 335/2025/NĐ-CP."
                    ),
                )
            )
