from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.projects.models import Project
from modules.projects.schemas import ProjectCreate, ProjectUpdate


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, project_id: int) -> Project | None:
        return self.db.get(Project, project_id)

    def list_all(self) -> list[Project]:
        stmt = select(Project).order_by(Project.id)
        return list(self.db.scalars(stmt).all())

    def list_by_user(self, user_id: int) -> list[Project]:
        stmt = select(Project).where(Project.user_id == user_id).order_by(Project.id)
        return list(self.db.scalars(stmt).all())

    def create(self, payload: ProjectCreate) -> Project:
        project = Project(
            user_id=payload.user_id,
            name=payload.name,
            prompt=payload.prompt,
            settings=payload.settings,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def update(self, project: Project, payload: ProjectUpdate) -> Project:
        if payload.name is not None:
            project.name = payload.name
        if payload.prompt is not None:
            project.prompt = payload.prompt
        if payload.settings is not None:
            project.settings = payload.settings
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.commit()
