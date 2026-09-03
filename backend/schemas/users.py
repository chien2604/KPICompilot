from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class PersonnelFields(BaseModel):
    """Define personnel profile fields shared by create and update requests."""

    full_name: str
    phone_number: str | None = None
    birth_year: int | None = None
    date_of_birth: date | None = None
    ethnicity: str = "Chưa cập nhật"
    party_joined_date: str = "Không ĐV"
    general_education: str = "Chưa cập nhật"
    professional_qualification: str = "Chưa cập nhật"
    political_theory: str = "Chưa cập nhật"
    position_title: str | None = None
    organization_role: str = "SPECIALIST"
    organization_domain: str = "UBND"
    manager_id: int | None = None
    management_scope_json: dict = Field(default_factory=dict)
    primary_position_code: str = "CHUA_XAC_DINH"
    personnel_type: str = "CONG_CHUC"
    is_kpi_eligible: bool = True
    source_work_area: str = "Chưa cập nhật"
    import_notes: str = ""
    department_id: int | None = None
    avatar_url: str | None = None


class UserOut(PersonnelFields):
    """Serialize a personnel profile and its account configuration."""

    id: int
    email: EmailStr | None = None
    role: str
    kpi_role_template: str
    permission_level: int
    department_name: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserCreate(PersonnelFields):
    """Validate a user account created manually by an administrator."""

    email: EmailStr
    password: str = Field(min_length=8)
    role: Literal["user"] = "user"
    kpi_role_template: str
    is_active: bool = True


class UserAccountUpdate(BaseModel):
    """Validate account, permission, and profile changes made by an administrator."""

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    role: Literal["admin", "user"] | None = None
    kpi_role_template: str | None = None
    position_title: str | None = None
    department_id: int | None = None
    is_active: bool | None = None
    phone_number: str | None = None
    birth_year: int | None = None
    ethnicity: str | None = None
    party_joined_date: str | None = None
    general_education: str | None = None
    professional_qualification: str | None = None
    political_theory: str | None = None
    organization_role: str | None = None
    organization_domain: str | None = None
    manager_id: int | None = None
    management_scope_json: dict | None = None
    primary_position_code: str | None = None
    personnel_type: str | None = None
    is_kpi_eligible: bool | None = None
    source_work_area: str | None = None
    import_notes: str | None = None

    @model_validator(mode="after")
    def reject_blank_email(self) -> "UserAccountUpdate":
        """Reject explicit blank email values while allowing omitted email updates."""

        if self.email is not None and not str(self.email).strip():
            raise ValueError("Email không được để trống.")
        return self


UserRoleUpdate = UserAccountUpdate


class PasswordResetRequest(BaseModel):
    """Validate an administrator password reset request."""

    new_password: str = Field(min_length=8)
