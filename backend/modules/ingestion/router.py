from fastapi import APIRouter, Depends, Query

from modules.ingestion.deps import get_ingestion_service
from modules.ingestion.schemas import (
    IngestionJobRead,
    ProjectStatsResponse,
    RefreshProjectResponse,
    RunIngestionRequest,
    RunIngestionResponse,
    ScheduleIngestionRequest,
)
from modules.ingestion.service import IngestionService


router = APIRouter()


@router.post("/schedule", response_model=IngestionJobRead)
def schedule_ingestion(
    payload: ScheduleIngestionRequest, service: IngestionService = Depends(get_ingestion_service)
) -> IngestionJobRead:
    job = service.schedule_source(payload.source_id, cron=payload.cron)
    return IngestionJobRead(id=job.id, source_id=job.source_id, cron=job.cron, status=job.status.value)


@router.post("/run/{job_id}", response_model=RunIngestionResponse)
def run_ingestion(
    job_id: int, payload: RunIngestionRequest, service: IngestionService = Depends(get_ingestion_service)
) -> RunIngestionResponse:
    chunks = service.run_job(job_id=job_id, raw_text=payload.raw_text)
    return RunIngestionResponse(job_id=job_id, chunks_created=len(chunks))


@router.post("/refresh/{project_id}", response_model=RefreshProjectResponse)
def refresh_project(
    project_id: int,
    trigger: str = Query(
        "auto",
        description="'auto' — по расписанию UI; 'manual' — кнопка (учитывается интервал в настройках проекта).",
    ),
    service: IngestionService = Depends(get_ingestion_service),
) -> RefreshProjectResponse:
    t = trigger.strip().lower()
    if t not in ("auto", "manual"):
        t = "auto"
    result = service.refresh_project(project_id, trigger=t)
    return RefreshProjectResponse(**result)


@router.get("/stats/{project_id}", response_model=ProjectStatsResponse)
def project_stats(project_id: int, service: IngestionService = Depends(get_ingestion_service)) -> ProjectStatsResponse:
    result = service.project_stats(project_id)
    return ProjectStatsResponse(**result)
