from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from modules.ingestion.models import IngestionJob, IngestionJobStatus, SourceChunk


class IngestionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_job(self, job_id: int) -> IngestionJob | None:
        return self.db.get(IngestionJob, job_id)

    def create_job(self, source_id: int, cron: str) -> IngestionJob:
        job = IngestionJob(source_id=source_id, cron=cron, status=IngestionJobStatus.PENDING)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_jobs(self) -> list[IngestionJob]:
        stmt = select(IngestionJob).order_by(IngestionJob.id)
        return list(self.db.scalars(stmt).all())

    def set_job_running(self, job: IngestionJob) -> IngestionJob:
        job.status = IngestionJobStatus.RUNNING
        job.last_error = None
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def set_job_done(self, job: IngestionJob) -> IngestionJob:
        job.status = IngestionJobStatus.DONE
        job.last_run_at = datetime.utcnow()
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def set_job_failed(self, job: IngestionJob, error: str) -> IngestionJob:
        job.status = IngestionJobStatus.FAILED
        job.last_error = error
        job.last_run_at = datetime.utcnow()
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def replace_chunks(self, source_id: int, chunks: list[str]) -> list[SourceChunk]:
        existing_stmt = select(SourceChunk).where(SourceChunk.source_id == source_id)
        existing = list(self.db.scalars(existing_stmt).all())
        for item in existing:
            self.db.delete(item)
        self.db.flush()

        created: list[SourceChunk] = []
        for idx, content in enumerate(chunks):
            chunk = SourceChunk(source_id=source_id, order_index=idx, content=content)
            self.db.add(chunk)
            created.append(chunk)

        self.db.commit()
        for chunk in created:
            self.db.refresh(chunk)
        return created

    def count_chunks_for_sources(self, source_ids: list[int]) -> int:
        if not source_ids:
            return 0
        stmt = select(func.count()).where(SourceChunk.source_id.in_(source_ids))
        return self.db.scalar(stmt) or 0

    def last_successful_job(self, source_ids: list[int]) -> IngestionJob | None:
        if not source_ids:
            return None
        stmt = (
            select(IngestionJob)
            .where(IngestionJob.source_id.in_(source_ids), IngestionJob.status == IngestionJobStatus.DONE)
            .order_by(IngestionJob.last_run_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
