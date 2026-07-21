from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    full_name: str
    email: str
    role: str
    kpi_role_template: str
    position_title: str | None
    department_id: int | None
    department_name: str | None
    avatar_url: str | None
    level: int  # cấp bậc phân quyền (0=Admin, 1=GĐ, 5=Chuyên viên)
    is_admin: bool = False  # True nếu role == "admin"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    email: str
    old_password: str
    new_password: str
