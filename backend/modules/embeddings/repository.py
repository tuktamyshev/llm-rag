from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.embeddings.models import EmbeddingRecord


class EmbeddingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_record(self, *, chunk_id: int, model_name: str, vector_size: int) -> EmbeddingRecord:
        stmt = select(EmbeddingRecord).where(EmbeddingRecord.chunk_id == chunk_id)
        record = self.db.scalar(stmt)
        if record:
            record.model_name = model_name
            record.vector_size = vector_size
        else:
            record = EmbeddingRecord(chunk_id=chunk_id, model_name=model_name, vector_size=vector_size)
            self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
