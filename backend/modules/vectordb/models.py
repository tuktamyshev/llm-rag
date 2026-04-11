from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.db import Base


class VectorRecord(Base):
    __tablename__ = "vector_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("source_chunks.id", ondelete="CASCADE"), unique=True, nullable=False)
    point_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    collection_name: Mapped[str] = mapped_column(String(128), nullable=False, default="source_chunks")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
