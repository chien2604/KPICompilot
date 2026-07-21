"""Script tạo tài khoản Admin đầu tiên cho hệ thống KPICompilot."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models.users import User
from core.security import hash_password


ADMIN_EMAIL = "admin@kpicompilot.gov.vn"
ADMIN_PASSWORD = "Admin@123"
ADMIN_NAME = "Quản trị viên hệ thống"


def create_admin():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if existing:
            existing.role = "admin"
            existing.full_name = ADMIN_NAME
            existing.hashed_password = hash_password(ADMIN_PASSWORD)
            existing.is_active = True
            db.commit()
            print(f"[OK] Cap nhat tai khoan admin: {ADMIN_EMAIL}")
        else:
            admin = User(
                full_name=ADMIN_NAME,
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                role="admin",
                kpi_role_template="CONG_CHUC_KHONG_CHUC_VU",
                position_title="Quan tri vien",
                department_id=None,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"[OK] Tao tai khoan admin thanh cong!")
            print(f"     Email   : {ADMIN_EMAIL}")
            print(f"     Password: {ADMIN_PASSWORD}")
            print(f"     User ID : {admin.id}")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
