from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class EmbeddingRecord(Base):
    __tablename__ = "embedding_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("source_chunks.id", ondelete="CASCADE"), unique=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, default="stub-hash-32")
    vector_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
