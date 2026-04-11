from fastapi import HTTPException, status

from modules.projects.models import Project
from modules.projects.repository import ProjectRepository
from modules.projects.schemas import ProjectCreate, ProjectUpdate
from modules.users.repository import UserRepository


class ProjectService:
    def __init__(self, projects: ProjectRepository, users: UserRepository) -> None:
        self.projects = projects
        self.users = users

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
        self.projects.delete(project)
