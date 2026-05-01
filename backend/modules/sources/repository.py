from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.sources.models import Source, SourceType


class SourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, source_id: int) -> Source | None:
        return self.db.get(Source, source_id)

    def list_by_project(self, project_id: int) -> list[Source]:
        stmt = select(Source).where(Source.project_id == project_id).order_by(Source.id)
        return list(self.db.scalars(stmt).all())

    def create(
        self,
        *,
        project_id: int,
        source_type: SourceType,
        title: str,
        uri: str | None,
        external_id: str | None,
        settings: dict,
    ) -> Source:
        source = Source(
            project_id=project_id,
            source_type=source_type,
            title=title,
            uri=uri,
            external_id=external_id,
            settings=settings,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def titles_for_source_ids(self, source_ids: list[int]) -> dict[int, str]:
        if not source_ids:
            return {}
        uniq = list(dict.fromkeys(source_ids))
        stmt = select(Source.id, Source.title).where(Source.id.in_(uniq))
        rows = self.db.execute(stmt).all()
        return {int(sid): str(title) for sid, title in rows}

    def delete(self, source: Source) -> None:
        self.db.delete(source)
        self.db.commit()
