"""
scripts/migrate_reports_to_blocks.py – Migration cho bảng `reports`.

LƯU Ý: Thiết kế JSON blocks (report_data) đã bị loại bỏ — báo cáo dùng HTML
trực tiếp (cột `content` đã có sẵn từ đầu) làm nguồn dữ liệu chính, sinh theo
report_generator_prompt.txt (yêu cầu tiêu ngữ hành chính + cấu trúc HTML cụ thể).

Script này chỉ còn cần:
1. Thêm cột `updated_at` (TIMESTAMP) nếu chưa tồn tại — dùng cho tính năng Edit
   (PATCH /reports/{id}) để biết lần sửa gần nhất.
2. KHÔNG cần convert dữ liệu cũ — báo cáo cũ (content là HTML từ report_generator
   cũ) vẫn hiển thị/export được bình thường, vì content luôn là HTML từ trước đến nay.

Nếu trước đó bạn đã chạy phiên bản migration cũ (có thêm cột `report_data`),
chạy thêm lệnh dưới đây 1 lần để dọn cột không dùng nữa (KHÔNG bắt buộc, an toàn
để giữ lại nếu muốn, cột thừa không ảnh hưởng hoạt động):

    ALTER TABLE reports DROP COLUMN IF EXISTS report_data;

Chạy: python scripts/migrate_reports_to_blocks.py
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND))

from sqlalchemy import text  # noqa: E402

from db.database import engine  # noqa: E402


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT now()"))
    print("[migrate] Đã đảm bảo cột updated_at tồn tại trên bảng reports.")
    print("[migrate] Báo cáo cũ (content dạng HTML) không cần convert, vẫn dùng được trực tiếp.")


if __name__ == "__main__":
    main()