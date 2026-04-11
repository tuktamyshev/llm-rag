from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from core.db import get_db
from modules.projects.repository import ProjectRepository
from modules.sources.repository import SourceRepository
from modules.sources.schemas import SourceRead, TelegramSourceCreate, WebSourceCreate
from modules.sources.service import SourceService


router = APIRouter()


def _service(db: Session = Depends(get_db)) -> SourceService:
    return SourceService(sources=SourceRepository(db), projects=ProjectRepository(db))


@router.post("/web", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def add_web_source(payload: WebSourceCreate, service: SourceService = Depends(_service)) -> SourceRead:
    source = service.add_web_source(payload)
    return SourceRead.model_validate(source)


@router.post("/telegram", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def add_telegram_source(payload: TelegramSourceCreate, service: SourceService = Depends(_service)) -> SourceRead:
    source = service.add_telegram_source(payload)
    return SourceRead.model_validate(source)


@router.get("/", response_model=list[SourceRead])
def list_sources(project_id: int, service: SourceService = Depends(_service)) -> list[SourceRead]:
    return [SourceRead.model_validate(item) for item in service.list_project_sources(project_id)]


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_source(source_id: int, service: SourceService = Depends(_service)) -> Response:
    service.delete(source_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
