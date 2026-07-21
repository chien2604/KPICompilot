from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    role: str
    kpi_role_template: str
    department_id: int | None = None
    position_title: str | None = None
    avatar_url: str | None = None
    is_active: bool = True


class UserOut(UserBase):
    id: int
    department_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdate(BaseModel):
    """Schema để admin cập nhật thông tin phân quyền của một user."""
    role: str | None = None                     # "staff" hoặc "admin"
    kpi_role_template: str | None = None        # BAN_GIAM_DOC / TRUONG_PHO_PHONG / CONG_CHUC_KHONG_CHUC_VU
    position_title: str | None = None           # Giám đốc, Phó Giám đốc, Trưởng phòng, ...
    department_id: int | None = None
    is_active: bool | None = None


class UserCreate(BaseModel):
    """Schema để admin tạo tài khoản người dùng mới."""
    full_name: str
    email: EmailStr
    password: str
    role: str = "staff"
    kpi_role_template: str = "CONG_CHUC_KHONG_CHUC_VU"
    position_title: str | None = None
    department_id: int | None = None
    avatar_url: str | None = None
    is_active: bool = True
