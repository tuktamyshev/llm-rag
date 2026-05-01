from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from modules.sources.models import SourceType


class SourceRead(BaseModel):
    id: int
    project_id: int
    source_type: SourceType
    title: str
    external_id: str | None
    uri: str | None
    settings: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class SourceCreatedResponse(SourceRead):
    """Ответ после создания источника: при необходимости — ошибка первичной индексации."""

    ingest_error: str | None = None
    chunks_indexed: int = 0


class WebSourceCreate(BaseModel):
    project_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    url: HttpUrl
    settings: dict[str, Any] = Field(default_factory=dict)


class TelegramSourceCreate(BaseModel):
    project_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    chat_id: str = Field(min_length=1, max_length=255)
    settings: dict[str, Any] = Field(default_factory=dict)
