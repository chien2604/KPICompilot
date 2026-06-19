from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from db.models.kpi import DocumentTypeRule, KPICriterion, KPITemplate


ROLE_TEMPLATES = {
    "BAN_GIAM_DOC": {
        "name": "Ban Giám đốc",
        "groups": [
            ("I", "Kỷ luật - kỷ cương hành chính", 15),
            ("II", "Hiệu quả thực hiện nhiệm vụ", 35),
            ("III", "Quản lý, điều hành", 20),
            ("IV", "Đạo đức công vụ", 20),
            ("V", "Phát triển năng lực", 10),
        ],
    },
    "TRUONG_PHO_PHONG": {
        "name": "Trưởng/phó phòng",
        "groups": [
            ("I", "Kỷ luật - kỷ cương hành chính", 15),
            ("II", "Hiệu quả thực hiện nhiệm vụ", 35),
            ("III", "Quản lý, điều hành", 20),
            ("IV", "Đạo đức công vụ", 20),
            ("V", "Phát triển năng lực", 10),
        ],
    },
    "CONG_CHUC_KHONG_CHUC_VU": {
        "name": "Công chức không giữ chức vụ",
        "groups": [
            ("I", "Kỷ luật - kỷ cương hành chính", 20),
            ("II", "Hiệu quả thực hiện nhiệm vụ", 50),
            ("III", "Đạo đức công vụ", 20),
            ("IV", "Phát triển năng lực", 10),
        ],
    },
}

DOCUMENT_RULES = [
    ("A", "Nhóm A", "Văn bản QPPL, đề án, chiến lược, quy hoạch, chương trình/kế hoạch dài hạn, nghị quyết, chỉ thị, báo cáo tổng kết nhiệm kỳ, hồ sơ trình cấp tỉnh.", "Hệ số ưu tiên cao do độ phức tạp và tác động lớn."),
    ("B", "Nhóm B", "Chương trình/kế hoạch năm, báo cáo năm, chuyên đề, quy chế, hướng dẫn nghiệp vụ, công văn tham mưu, tờ trình.", "Hệ số chuẩn cho nhiệm vụ chuyên môn quan trọng."),
    ("C", "Nhóm C", "Báo cáo tháng/quý, văn bản trả lời, hồ sơ thủ tục hành chính, thống kê định kỳ, công văn phối hợp, báo cáo nhanh.", "Hệ số trung bình cho nhiệm vụ thường xuyên."),
    ("D", "Nhóm D", "Báo cáo tuần, góp ý, trao đổi nội bộ, giấy mời, biên bản họp, văn bản cung cấp thông tin, phiếu chuyển.", "Hệ số thấp hơn do độ phức tạp thấp."),
]


class ExcelRuleLoader:
    def __init__(self, db: Session, root_dir: Path) -> None:
        self.db = db
        self.root_dir = root_dir

    def seed(self) -> None:
        self._touch_excel_files()
        self.db.query(KPICriterion).delete()
        self.db.query(KPITemplate).delete()
        self.db.query(DocumentTypeRule).delete()
        for code, spec in ROLE_TEMPLATES.items():
            template = KPITemplate(code=code, name=spec["name"], target_role=code, total_score=100)
            self.db.add(template)
            self.db.flush()
            sort_order = 1
            for group_code, group_name, max_score in spec["groups"]:
                self.db.add(
                    KPICriterion(
                        template_id=template.id,
                        group_code=group_code,
                        group_name=group_name,
                        criterion_code=f"{code}_{group_code}",
                        criterion_name=group_name,
                        description=f"Nhóm tiêu chí {group_name} cho {spec['name']}.",
                        calculation_rule_text="Rule Engine tính dựa trên tiến độ nhiệm vụ, hạn xử lý, loại văn bản, minh chứng và điểm tự/leader đánh giá.",
                        max_score=max_score,
                        sort_order=sort_order,
                    )
                )
                sort_order += 1
        for code, name, description, scoring in DOCUMENT_RULES:
            self.db.add(DocumentTypeRule(code=code, name=name, description=description, scoring_rule_text=scoring))
        self.db.commit()

    def _touch_excel_files(self) -> None:
        candidates = [
            "BAN GIAM DOC dx1(1).xlsx",
            "BAN GIAM DOC dx1.xlsx",
            "TRUONG PHO PHONG dx(1).xlsx",
            "TRUONG PHO PHONG dx.xlsx",
            "KHONG CHUC VU dx(1).xlsx",
            "KHONG CHUC VU dx.xlsx",
        ]
        for name in candidates:
            path = self.root_dir / name
            if path.exists():
                try:
                    workbook = load_workbook(path, read_only=True, data_only=True)
                    workbook.close()
                except Exception:
                    pass
