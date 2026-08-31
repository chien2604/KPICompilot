from typing import TYPE_CHECKING

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base

if TYPE_CHECKING:
    from db.models.departments import Department


class User(Base):
    """Store personnel profile, account state, position, and KPI role."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="user", nullable=False)
    kpi_role_template: Mapped[str] = mapped_column(String(80), nullable=False)
    permission_level: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    organization_role: Mapped[str] = mapped_column(
        String(40), default="SPECIALIST", nullable=False, index=True
    )
    primary_position_code: Mapped[str] = mapped_column(
        String(80), default="CHUA_XAC_DINH", nullable=False
    )
    personnel_type: Mapped[str] = mapped_column(
        String(30), default="CONG_CHUC", nullable=False
    )
    is_kpi_eligible: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    position_title: Mapped[str | None] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True
    )
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    ethnicity: Mapped[str] = mapped_column(
        String(100), default="Chưa cập nhật", nullable=False
    )
    party_joined_date: Mapped[str] = mapped_column(
        String(30), default="Không ĐV", nullable=False
    )
    general_education: Mapped[str] = mapped_column(
        String(50), default="Chưa cập nhật", nullable=False
    )
    professional_qualification: Mapped[str] = mapped_column(
        String(100), default="Chưa cập nhật", nullable=False
    )
    political_theory: Mapped[str] = mapped_column(
        String(100), default="Chưa cập nhật", nullable=False
    )
    source_work_area: Mapped[str] = mapped_column(
        Text, default="Chưa cập nhật", nullable=False
    )
    import_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    department: Mapped["Department | None"] = relationship(back_populates="users")
    work_areas: Mapped[list["UserWorkArea"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserWorkArea(Base):
    """Store one normalized work area assigned to a personnel profile."""

    __tablename__ = "user_work_areas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    area_code: Mapped[str] = mapped_column(String(40), nullable=False)
    area_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="work_areas")
