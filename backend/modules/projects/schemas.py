from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    prompt: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(ProjectBase):
    user_id: int = Field(gt=0)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    prompt: str | None = None
    settings: dict[str, Any] | None = None


class ProjectRead(ProjectBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
