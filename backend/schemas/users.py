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
