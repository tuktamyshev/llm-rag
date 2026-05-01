"""Общая фабрика зависимостей для IngestionService (роутеры ingestion и sources)."""

from fastapi import Depends
from sqlalchemy.orm import Session

from core.db import get_db
from modules.embeddings.repository import EmbeddingRepository
from modules.embeddings.service import EmbeddingService
from modules.ingestion.repository import IngestionRepository
from modules.ingestion.service import IngestionService
from modules.projects.repository import ProjectRepository
from modules.sources.repository import SourceRepository
from modules.vectordb.repository import QdrantRepository, VectorRecordRepository
from modules.vectordb.service import VectorDBService


def get_ingestion_service(db: Session = Depends(get_db)) -> IngestionService:
    ingestion_repo = IngestionRepository(db)
    source_repo = SourceRepository(db)
    embedding_service = EmbeddingService(EmbeddingRepository(db))
    vectordb_service = VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository())
    return IngestionService(
        ingestion=ingestion_repo,
        sources=source_repo,
        embeddings=embedding_service,
        vectordb=vectordb_service,
        projects=ProjectRepository(db),
    )

