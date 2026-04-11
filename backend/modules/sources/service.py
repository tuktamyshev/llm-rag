from fastapi import HTTPException, status

from modules.projects.repository import ProjectRepository
from modules.sources.models import Source, SourceType
from modules.sources.repository import SourceRepository
from modules.sources.schemas import TelegramSourceCreate, WebSourceCreate


class SourceService:
    def __init__(self, sources: SourceRepository, projects: ProjectRepository) -> None:
        self.sources = sources
        self.projects = projects

    def add_web_source(self, payload: WebSourceCreate) -> Source:
        self._ensure_project_exists(payload.project_id)
        return self.sources.create(
            project_id=payload.project_id,
            source_type=SourceType.WEB,
            title=payload.title,
            uri=str(payload.url),
            external_id=None,
            settings=payload.settings,
        )

    def add_telegram_source(self, payload: TelegramSourceCreate) -> Source:
        self._ensure_project_exists(payload.project_id)
        return self.sources.create(
            project_id=payload.project_id,
            source_type=SourceType.TELEGRAM,
            title=payload.title,
            uri=None,
            external_id=payload.chat_id,
            settings=payload.settings,
        )

    def list_project_sources(self, project_id: int) -> list[Source]:
        self._ensure_project_exists(project_id)
        return self.sources.list_by_project(project_id)

    def delete(self, source_id: int) -> None:
        source = self.sources.get_by_id(source_id)
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
        self.sources.delete(source)

    def _ensure_project_exists(self, project_id: int) -> None:
        project = self.projects.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
