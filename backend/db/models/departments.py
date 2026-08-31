from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base

if TYPE_CHECKING:
    from db.models.users import User


class Department(Base):
    """Represent the organization root or a commune administrative unit."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    unit_type: Mapped[str] = mapped_column(
        String(30), default="UNIT", nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )

    parent: Mapped["Department | None"] = relationship(remote_side=[id])
    users: Mapped[list["User"]] = relationship(back_populates="department")
