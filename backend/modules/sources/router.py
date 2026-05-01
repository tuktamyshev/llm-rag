from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from core.db import get_db
from modules.ingestion.background_ingest import ingest_source_background
from modules.ingestion.repository import IngestionRepository
from modules.projects.repository import ProjectRepository
from modules.sources.repository import SourceRepository
from modules.sources.models import Source
from modules.sources.schemas import SourceCreatedResponse, SourceRead, TelegramSourceCreate, WebSourceCreate
from modules.sources.service import SourceService
from modules.vectordb.repository import QdrantRepository, VectorRecordRepository
from modules.vectordb.service import VectorDBService


router = APIRouter()


def _wrap_created_async(source: Source, background_tasks: BackgroundTasks) -> SourceCreatedResponse:
    background_tasks.add_task(ingest_source_background, source.id)
    base = SourceRead.model_validate(source)
    return SourceCreatedResponse(
        **base.model_dump(),
        ingest_error=None,
        chunks_indexed=0,
        ingest_in_background=True,
    )


def _service(db: Session = Depends(get_db)) -> SourceService:
    return SourceService(
        sources=SourceRepository(db),
        projects=ProjectRepository(db),
        ingestion=IngestionRepository(db),
        vectordb=VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository()),
    )


@router.post("/file", response_model=SourceCreatedResponse, status_code=status.HTTP_201_CREATED)
async def add_file_source(
    background_tasks: BackgroundTasks,
    project_id: int = Form(...),
    title: str = Form(..., min_length=1, max_length=255),
    file: UploadFile = File(...),
    service: SourceService = Depends(_service),
) -> SourceCreatedResponse:
    if project_id <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid project_id")

    raw = await file.read()
    source = service.add_file_source(
        project_id=project_id,
        title=title.strip(),
        original_filename=file.filename or "upload",
        data=raw,
    )
    return _wrap_created_async(source, background_tasks)


@router.post("/web", response_model=SourceCreatedResponse, status_code=status.HTTP_201_CREATED)
def add_web_source(
    background_tasks: BackgroundTasks,
    payload: WebSourceCreate,
    service: SourceService = Depends(_service),
) -> SourceCreatedResponse:
    source = service.add_web_source(payload)
    return _wrap_created_async(source, background_tasks)


@router.post("/telegram", response_model=SourceCreatedResponse, status_code=status.HTTP_201_CREATED)
def add_telegram_source(
    background_tasks: BackgroundTasks,
    payload: TelegramSourceCreate,
    service: SourceService = Depends(_service),
) -> SourceCreatedResponse:
    source = service.add_telegram_source(payload)
    return _wrap_created_async(source, background_tasks)


@router.get("/", response_model=list[SourceRead])
def list_sources(project_id: int, service: SourceService = Depends(_service)) -> list[SourceRead]:
    return [SourceRead.model_validate(item) for item in service.list_project_sources(project_id)]


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_source(source_id: int, service: SourceService = Depends(_service)) -> Response:
    service.delete(source_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
