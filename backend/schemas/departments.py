from pydantic import BaseModel, ConfigDict


class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
