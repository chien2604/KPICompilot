from pydantic import BaseModel, ConfigDict


class DepartmentOut(BaseModel):
    """Serialize an organization unit."""

    id: int
    name: str
    code: str
    unit_type: str
    parent_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
