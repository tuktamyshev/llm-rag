from pydantic import BaseModel, Field


class EmbeddingPointIn(BaseModel):
    chunk_id: int = Field(gt=0)
    source_id: int = Field(gt=0)
    project_id: int = Field(gt=0)
    content: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=1)


class UpsertEmbeddingsRequest(BaseModel):
    points: list[EmbeddingPointIn] = Field(min_length=1)


class UpsertEmbeddingsResponse(BaseModel):
    upserted: int
    collection_name: str
    vector_size: int


class TopKSearchRequest(BaseModel):
    project_id: int = Field(gt=0)
    query_embedding: list[float] = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)


class TopKChunk(BaseModel):
    chunk_id: int
    source_id: int
    project_id: int
    content: str
    score: float


class TopKSearchResponse(BaseModel):
    collection_name: str
    items: list[TopKChunk]
