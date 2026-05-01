from datetime import datetime, timezone

from fastapi import HTTPException, status

from modules.embeddings.service import EmbeddingService
from modules.ingestion.collectors import collect_source_text
from modules.ingestion.chunking import chunk_text
from modules.ingestion.cleaning import clean_text
from modules.ingestion.models import IngestionJob, SourceChunk
from modules.ingestion.repository import IngestionRepository
from modules.ingestion.scheduler import should_run
from modules.projects.ingestion_settings import manual_refresh_cooldown_seconds, parse_iso_utc
from modules.projects.repository import ProjectRepository
from modules.projects.schemas import ProjectUpdate
from modules.sources.models import Source
from modules.sources.repository import SourceRepository
from modules.vectordb.schemas import EmbeddingPointIn, UpsertEmbeddingsRequest
from modules.vectordb.service import VectorDBService


class IngestionService:
    def __init__(
        self,
        ingestion: IngestionRepository,
        sources: SourceRepository,
        embeddings: EmbeddingService,
        vectordb: VectorDBService,
        projects: ProjectRepository,
    ) -> None:
        self.ingestion = ingestion
        self.sources = sources
        self.embeddings = embeddings
        self.vectordb = vectordb
        self.projects = projects

    def schedule_source(self, source_id: int, cron: str = "*/30 * * * *") -> IngestionJob:
        source = self.sources.get_by_id(source_id)
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
        return self.ingestion.create_job(source_id=source_id, cron=cron)

    def _ingest_source(self, source: Source, raw_text: str | None = None) -> list[SourceChunk]:
        """Collect → clean → chunk → embed → upsert for a single source."""
        source_text = raw_text if raw_text is not None else collect_source_text(source)
        cleaned = clean_text(source_text)
        chunks = chunk_text(cleaned)
        # Удаляем старые векторы в Qdrant до смены chunk id в БД — иначе остаются «сироты» с тем же project_id.
        old_chunk_ids = self.ingestion.list_chunk_ids_for_source(source.id)
        if old_chunk_ids:
            self.vectordb.delete_embeddings_for_chunk_ids(old_chunk_ids)
        created = self.ingestion.replace_chunks(source_id=source.id, chunks=chunks)
        embedded_chunks = self.embeddings.embed_and_track_chunks(
            [
                {
                    "chunk_id": chunk.id,
                    "source_id": source.id,
                    "project_id": source.project_id,
                    "content": chunk.content,
                }
                for chunk in created
            ]
        )
        if embedded_chunks:
            self.vectordb.upsert_embeddings(
                UpsertEmbeddingsRequest(
                    points=[
                        EmbeddingPointIn(
                            chunk_id=item.chunk_id,
                            source_id=item.source_id,
                            project_id=item.project_id,
                            content=item.content,
                            embedding=item.embedding,
                        )
                        for item in embedded_chunks
                    ]
                )
            )
        return created

    def ingest_source_now(self, source: Source, raw_text: str | None = None) -> list[SourceChunk]:
        """Полный сбор и индексация одного источника (без записи ingestion job)."""
        return self._ingest_source(source, raw_text=raw_text)

    def run_job(self, job_id: int, raw_text: str | None = None, now: datetime | None = None) -> list[SourceChunk]:
        job = self.ingestion.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found")

        source = self.sources.get_by_id(job.source_id)
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

        if not should_run(job.cron, now=now):
            return []

        self.ingestion.set_job_running(job)
        try:
            created = self._ingest_source(source, raw_text=raw_text)
            self.ingestion.set_job_done(job)
            return created
        except Exception as exc:
            self.ingestion.set_job_failed(job, error=str(exc))
            raise

    def _ensure_manual_refresh_allowed(self, project_id: int) -> None:
        project = self.projects.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        cooldown = manual_refresh_cooldown_seconds(project.settings)
        if cooldown <= 0:
            return
        ps = project.settings or {}
        ing = ps.get("ingestion") if isinstance(ps.get("ingestion"), dict) else {}
        last_raw = ing.get("last_manual_refresh_at")
        last = parse_iso_utc(last_raw) if isinstance(last_raw, str) else None
        if last is None:
            return
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        if elapsed < cooldown:
            wait = int(cooldown - elapsed) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Повторное обновление вручную доступно через {wait} с.",
            )

    def _record_manual_refresh(self, project_id: int) -> None:
        project = self.projects.get_by_id(project_id)
        if not project:
            return
        settings = dict(project.settings or {})
        ing = dict(settings.get("ingestion") or {})
        ing["last_manual_refresh_at"] = datetime.now(timezone.utc).isoformat()
        settings["ingestion"] = ing
        self.projects.update(project, ProjectUpdate(settings=settings))

    def refresh_project(self, project_id: int, *, trigger: str = "auto") -> dict:
        """Force-ingest all sources for a project. Skips cron check."""
        if trigger == "manual":
            self._ensure_manual_refresh_allowed(project_id)

        sources = self.sources.list_by_project(project_id)
        if not sources:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sources for this project")

        total_chunks = 0
        errors: list[str] = []
        for source in sources:
            job = self.ingestion.create_job(source_id=source.id, cron="manual")
            self.ingestion.set_job_running(job)
            try:
                created = self._ingest_source(source)
                self.ingestion.set_job_done(job)
                total_chunks += len(created)
            except Exception as exc:
                self.ingestion.set_job_failed(job, error=str(exc))
                errors.append(f"{source.title}: {exc}")

        if trigger == "manual":
            self._record_manual_refresh(project_id)

        n_ok = len(sources) - len(errors)

        return {
            "project_id": project_id,
            "sources_processed": len(sources),
            "sources_succeeded": n_ok,
            "sources_failed": len(errors),
            "total_chunks": total_chunks,
            "errors": errors,
        }

    def project_stats(self, project_id: int) -> dict:
        """Return ingestion statistics for a project."""
        sources = self.sources.list_by_project(project_id)
        source_ids = [s.id for s in sources]
        chunks = self.ingestion.count_chunks_for_sources(source_ids) if source_ids else 0
        last_job = self.ingestion.last_successful_job(source_ids) if source_ids else None
        return {
            "project_id": project_id,
            "sources_count": len(sources),
            "chunks_count": chunks,
            "last_updated": last_job.last_run_at.isoformat() if last_job and last_job.last_run_at else None,
        }
