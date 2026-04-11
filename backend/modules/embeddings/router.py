from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from modules.embeddings.repository import EmbeddingRepository
from modules.embeddings.schemas import EmbedChunksRequest, EmbedChunksResponse, EmbedTextRequest, EmbedTextResponse
from modules.embeddings.service import EmbeddingService, MODEL_NAME, embed_text


router = APIRouter()


def _service(db: Session = Depends(get_db)) -> EmbeddingService:
    return EmbeddingService(repository=EmbeddingRepository(db))


@router.post("/text", response_model=EmbedTextResponse)
def embed_single_text(payload: EmbedTextRequest) -> EmbedTextResponse:
    return EmbedTextResponse(embedding=embed_text(payload.text, size=payload.size), model_name=MODEL_NAME)


@router.post("/chunks", response_model=EmbedChunksResponse)
def embed_chunks(payload: EmbedChunksRequest, service: EmbeddingService = Depends(_service)) -> EmbedChunksResponse:
    items = service.embed_and_track_chunks(
        [
            {
                "chunk_id": chunk.chunk_id,
                "source_id": chunk.source_id,
                "project_id": chunk.project_id,
                "content": chunk.content,
            }
            for chunk in payload.chunks
        ],
        size=payload.size,
    )
    return EmbedChunksResponse(items=items, model_name=MODEL_NAME)
