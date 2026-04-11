from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from modules.embeddings.repository import EmbeddingRepository
from modules.embeddings.service import EmbeddingService
from modules.ingestion.repository import IngestionRepository
from modules.ingestion.schemas import (
    IngestionJobRead,
    ProjectStatsResponse,
    RefreshProjectResponse,
    RunIngestionRequest,
    RunIngestionResponse,
    ScheduleIngestionRequest,
)
from modules.ingestion.service import IngestionService
from modules.sources.repository import SourceRepository
from modules.vectordb.repository import QdrantRepository, VectorRecordRepository
from modules.vectordb.service import VectorDBService


router = APIRouter()


def _service(db: Session = Depends(get_db)) -> IngestionService:
    ingestion_repo = IngestionRepository(db)
    source_repo = SourceRepository(db)
    embedding_service = EmbeddingService(EmbeddingRepository(db))
    vectordb_service = VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository())
    return IngestionService(
        ingestion=ingestion_repo,
        sources=source_repo,
        embeddings=embedding_service,
        vectordb=vectordb_service,
    )


@router.post("/schedule", response_model=IngestionJobRead)
def schedule_ingestion(
    payload: ScheduleIngestionRequest, service: IngestionService = Depends(_service)
) -> IngestionJobRead:
    job = service.schedule_source(payload.source_id, cron=payload.cron)
    return IngestionJobRead(id=job.id, source_id=job.source_id, cron=job.cron, status=job.status.value)


@router.post("/run/{job_id}", response_model=RunIngestionResponse)
def run_ingestion(
    job_id: int, payload: RunIngestionRequest, service: IngestionService = Depends(_service)
) -> RunIngestionResponse:
    chunks = service.run_job(job_id=job_id, raw_text=payload.raw_text)
    return RunIngestionResponse(job_id=job_id, chunks_created=len(chunks))


@router.post("/refresh/{project_id}", response_model=RefreshProjectResponse)
def refresh_project(project_id: int, service: IngestionService = Depends(_service)) -> RefreshProjectResponse:
    result = service.refresh_project(project_id)
    return RefreshProjectResponse(**result)


@router.get("/stats/{project_id}", response_model=ProjectStatsResponse)
def project_stats(project_id: int, service: IngestionService = Depends(_service)) -> ProjectStatsResponse:
    result = service.project_stats(project_id)
    return ProjectStatsResponse(**result)
