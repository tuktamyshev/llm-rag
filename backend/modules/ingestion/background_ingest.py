"""Фоновая индексация источника после создания записи (не блокировать HTTP-ответ)."""

from __future__ import annotations

import asyncio
import logging

from core.db import SessionLocal
from modules.embeddings.repository import EmbeddingRepository
from modules.embeddings.service import EmbeddingService
from modules.ingestion.repository import IngestionRepository
from modules.ingestion.service import IngestionService
from modules.projects.repository import ProjectRepository
from modules.sources.repository import SourceRepository
from modules.vectordb.repository import QdrantRepository, VectorRecordRepository
from modules.vectordb.service import VectorDBService

logger = logging.getLogger(__name__)


def _ingest_source_sync(source_id: int) -> None:
    """Синхронная индексация (вызывать из thread pool — не из event loop)."""
    db = SessionLocal()
    try:
        svc = IngestionService(
            ingestion=IngestionRepository(db),
            sources=SourceRepository(db),
            embeddings=EmbeddingService(EmbeddingRepository(db)),
            vectordb=VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository()),
            projects=ProjectRepository(db),
        )
        source = svc.sources.get_by_id(source_id)
        if not source:
            logger.warning("ingest_source_background: источник id=%s не найден", source_id)
            return
        svc.ingest_source_now(source)
        logger.info("ingest_source_background: готово source_id=%s", source_id)
    except Exception:
        logger.exception("ingest_source_background: ошибка source_id=%s", source_id)
    finally:
        db.close()


async def ingest_source_background(source_id: int) -> None:
    """Планируется в BackgroundTasks: тяжёлая работа в пуле потоков, не блокирует asyncio."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _ingest_source_sync, source_id)
