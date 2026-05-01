from fastapi import HTTPException, status

from modules.projects.models import Project
from modules.projects.repository import ProjectRepository
from modules.projects.schemas import ProjectCreate, ProjectUpdate
from modules.sources.file_storage import delete_stored_file_if_exists
from modules.sources.models import SourceType
from modules.sources.repository import SourceRepository
from modules.ingestion.repository import IngestionRepository
from modules.users.repository import UserRepository
from modules.vectordb.service import VectorDBService


class ProjectService:
    def __init__(
        self,
        projects: ProjectRepository,
        users: UserRepository,
        *,
        sources: SourceRepository | None = None,
        ingestion: IngestionRepository | None = None,
        vectordb: VectorDBService | None = None,
    ) -> None:
        self.projects = projects
        self.users = users
        self.sources = sources
        self.ingestion = ingestion
        self.vectordb = vectordb

    def create(self, payload: ProjectCreate) -> Project:
        owner = self.users.get_by_id(payload.user_id)
        if not owner:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner user not found")
        return self.projects.create(payload)

    def get(self, project_id: int) -> Project:
        project = self.projects.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    def list(self, user_id: int | None = None) -> list[Project]:
        if user_id is None:
            return self.projects.list_all()
        return self.projects.list_by_user(user_id)

    def update(self, project_id: int, payload: ProjectUpdate) -> Project:
        project = self.get(project_id)
        return self.projects.update(project, payload)

    def delete(self, project_id: int) -> None:
        project = self.get(project_id)
        if self.sources and self.ingestion and self.vectordb:
            src_list = self.sources.list_by_project(project_id)
            chunk_ids: list[int] = []
            for s in src_list:
                chunk_ids.extend(self.ingestion.list_chunk_ids_for_source(s.id))
                if s.source_type == SourceType.FILE:
                    delete_stored_file_if_exists((s.settings or {}).get("file_relpath"))
            if chunk_ids:
                self.vectordb.delete_embeddings_for_chunk_ids(chunk_ids)
        self.projects.delete(project)
