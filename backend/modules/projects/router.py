from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from core.db import get_db
from modules.projects.repository import ProjectRepository
from modules.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from modules.projects.service import ProjectService
from modules.users.repository import UserRepository


router = APIRouter()


def _service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(projects=ProjectRepository(db), users=UserRepository(db))


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, service: ProjectService = Depends(_service)) -> ProjectRead:
    project = service.create(payload)
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, service: ProjectService = Depends(_service)) -> ProjectRead:
    project = service.get(project_id)
    return ProjectRead.model_validate(project)


@router.get("/", response_model=list[ProjectRead])
def list_projects(user_id: int | None = None, service: ProjectService = Depends(_service)) -> list[ProjectRead]:
    projects = service.list(user_id=user_id)
    return [ProjectRead.model_validate(project) for project in projects]


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int, payload: ProjectUpdate, service: ProjectService = Depends(_service)
) -> ProjectRead:
    project = service.update(project_id, payload)
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_project(project_id: int, service: ProjectService = Depends(_service)) -> Response:
    service.delete(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
