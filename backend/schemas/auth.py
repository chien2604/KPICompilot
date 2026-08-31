from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Validate email and password login input."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Return the authenticated account and access token."""

    access_token: str
    token_type: str = "bearer"
    user_id: int
    full_name: str
    email: str | None
    role: str
    kpi_role_template: str
    organization_role: str
    position_title: str | None
    department_id: int | None
    department_name: str | None
    avatar_url: str | None
    level: int
    is_admin: bool = False


class ChangePasswordRequest(BaseModel):
    """Validate an authenticated password change."""

    old_password: str
    new_password: str = Field(min_length=8)


class ResetPasswordRequest(BaseModel):
    """Validate a public password change using existing credentials."""

    email: EmailStr
    old_password: str
    new_password: str = Field(min_length=8)
