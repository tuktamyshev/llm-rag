from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from core.db import get_db
from modules.ingestion.repository import IngestionRepository
from modules.projects.repository import ProjectRepository
from modules.sources.repository import SourceRepository
from modules.ingestion.deps import get_ingestion_service
from modules.ingestion.service import IngestionService
from modules.sources.models import Source
from modules.sources.schemas import SourceCreatedResponse, SourceRead, TelegramSourceCreate, WebSourceCreate
from modules.sources.service import SourceService
from modules.vectordb.repository import QdrantRepository, VectorRecordRepository
from modules.vectordb.service import VectorDBService


router = APIRouter()


def _ingest_and_wrap(source: Source, ingestion: IngestionService) -> SourceCreatedResponse:
    n = 0
    err: str | None = None
    try:
        created = ingestion.ingest_source_now(source)
        n = len(created)
    except Exception as exc:
        err = str(exc)
    base = SourceRead.model_validate(source)
    return SourceCreatedResponse(**base.model_dump(), ingest_error=err, chunks_indexed=n)


def _service(db: Session = Depends(get_db)) -> SourceService:
    return SourceService(
        sources=SourceRepository(db),
        projects=ProjectRepository(db),
        ingestion=IngestionRepository(db),
        vectordb=VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository()),
    )


@router.post("/file", response_model=SourceCreatedResponse, status_code=status.HTTP_201_CREATED)
async def add_file_source(
    project_id: int = Form(...),
    title: str = Form(..., min_length=1, max_length=255),
    file: UploadFile = File(...),
    service: SourceService = Depends(_service),
    ingestion: IngestionService = Depends(get_ingestion_service),
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
    return _ingest_and_wrap(source, ingestion)


@router.post("/web", response_model=SourceCreatedResponse, status_code=status.HTTP_201_CREATED)
def add_web_source(
    payload: WebSourceCreate,
    service: SourceService = Depends(_service),
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> SourceCreatedResponse:
    source = service.add_web_source(payload)
    return _ingest_and_wrap(source, ingestion)


@router.post("/telegram", response_model=SourceCreatedResponse, status_code=status.HTTP_201_CREATED)
def add_telegram_source(
    payload: TelegramSourceCreate,
    service: SourceService = Depends(_service),
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> SourceCreatedResponse:
    source = service.add_telegram_source(payload)
    return _ingest_and_wrap(source, ingestion)


@router.get("/", response_model=list[SourceRead])
def list_sources(project_id: int, service: SourceService = Depends(_service)) -> list[SourceRead]:
    return [SourceRead.model_validate(item) for item in service.list_project_sources(project_id)]


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_source(source_id: int, service: SourceService = Depends(_service)) -> Response:
    service.delete(source_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
