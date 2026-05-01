from fastapi import HTTPException, status

from modules.ingestion.repository import IngestionRepository
from modules.projects.repository import ProjectRepository
from modules.sources.file_storage import MAX_FILE_BYTES, delete_stored_file_if_exists, store_project_file
from modules.sources.models import Source, SourceType
from modules.sources.repository import SourceRepository
from modules.sources.schemas import TelegramSourceCreate, WebSourceCreate
from modules.vectordb.service import VectorDBService


class SourceService:
    def __init__(
        self,
        sources: SourceRepository,
        projects: ProjectRepository,
        ingestion: IngestionRepository | None = None,
        vectordb: VectorDBService | None = None,
    ) -> None:
        self.sources = sources
        self.projects = projects
        self.ingestion = ingestion
        self.vectordb = vectordb

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

    def add_file_source(self, *, project_id: int, title: str, original_filename: str, data: bytes) -> Source:
        self._ensure_project_exists(project_id)
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Файл больше {MAX_FILE_BYTES // (1024 * 1024)} МБ",
            )
        if len(data) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой файл")

        relpath, _abs_path = store_project_file(project_id, original_filename, data)
        settings = {
            "file_relpath": relpath,
            "original_filename": original_filename,
        }
        return self.sources.create(
            project_id=project_id,
            source_type=SourceType.FILE,
            title=title,
            uri=None,
            external_id=None,
            settings=settings,
        )

    def list_project_sources(self, project_id: int) -> list[Source]:
        self._ensure_project_exists(project_id)
        return self.sources.list_by_project(project_id)

    def delete(self, source_id: int) -> None:
        source = self.sources.get_by_id(source_id)
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

        # 1) Векторы в Qdrant (id точки = chunk_id)
        if self.ingestion and self.vectordb:
            chunk_ids = self.ingestion.list_chunk_ids_for_source(source_id)
            if chunk_ids:
                self.vectordb.delete_embeddings_for_chunk_ids(chunk_ids)

        # 2) Чанки и связанные строки в PostgreSQL (эмбеддинг-метаданные, vector_records — CASCADE)
        if self.ingestion:
            self.ingestion.delete_all_chunks_for_source(source_id)

        if source.source_type == SourceType.FILE:
            delete_stored_file_if_exists((source.settings or {}).get("file_relpath"))

        # 3) Сам источник и ingestion_jobs — CASCADE
        self.sources.delete(source)

    def _ensure_project_exists(self, project_id: int) -> None:
        project = self.projects.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
