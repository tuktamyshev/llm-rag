from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from modules.vectordb.repository import QdrantRepository, VectorRecordRepository
from modules.vectordb.schemas import (
    TopKSearchRequest,
    TopKSearchResponse,
    UpsertEmbeddingsRequest,
    UpsertEmbeddingsResponse,
)
from modules.vectordb.service import VectorDBService


router = APIRouter()


def _service(db: Session = Depends(get_db)) -> VectorDBService:
    return VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository())


@router.post("/upsert", response_model=UpsertEmbeddingsResponse)
def upsert_embeddings(
    payload: UpsertEmbeddingsRequest, service: VectorDBService = Depends(_service)
) -> UpsertEmbeddingsResponse:
    result = service.upsert_embeddings(payload)
    return UpsertEmbeddingsResponse(**result)


@router.post("/search", response_model=TopKSearchResponse)
def search_top_k(payload: TopKSearchRequest, service: VectorDBService = Depends(_service)) -> TopKSearchResponse:
    return service.search_top_k(payload)
