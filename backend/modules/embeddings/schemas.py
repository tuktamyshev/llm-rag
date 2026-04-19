from pydantic import BaseModel, Field


class EmbedTextRequest(BaseModel):
    text: str = Field(min_length=1)


class EmbedTextResponse(BaseModel):
    embedding: list[float]
    model_name: str


class ChunkIn(BaseModel):
    chunk_id: int = Field(gt=0)
    source_id: int = Field(gt=0)
    project_id: int = Field(gt=0)
    content: str = Field(min_length=1)


class EmbedChunksRequest(BaseModel):
    chunks: list[ChunkIn] = Field(min_length=1)


class EmbeddedChunk(BaseModel):
    chunk_id: int
    source_id: int
    project_id: int
    content: str
    embedding: list[float]


class EmbedChunksResponse(BaseModel):
    items: list[EmbeddedChunk]
    model_name: str
