from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    project_id: int = Field(gt=0)
    query: str = Field(default="", min_length=0)
    query_embedding: list[float] = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class RetrievedChunk(BaseModel):
    chunk_id: int
    source_id: int
    content: str
    score: float


class RetrieveResponse(BaseModel):
    items: list[RetrievedChunk]


class AskRAGRequest(BaseModel):
    project_id: int = Field(gt=0)
    query: str = Field(min_length=1)
    query_embedding: list[float] | None = Field(default=None, min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class AskRAGResponse(BaseModel):
    answer: str
    context_chunks: list[RetrievedChunk]
