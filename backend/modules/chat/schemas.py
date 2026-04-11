from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    query_embedding: list[float] | None = Field(default=None, min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)


class ChatLogRead(BaseModel):
    id: int
    project_id: int
    question: str
    answer: str
    sources: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
