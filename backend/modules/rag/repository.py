from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.rag.models import RAGQueryLog
from modules.rag.schemas import RetrievedChunk


class RAGLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_log(
        self,
        *,
        project_id: int,
        question: str,
        retrieved_context: list[RetrievedChunk],
        answer: str,
    ) -> RAGQueryLog:
        context_payload = [
            {
                "chunk_id": item.chunk_id,
                "source_id": item.source_id,
                "content": item.content,
                "score": item.score,
            }
            for item in retrieved_context
        ]
        log = RAGQueryLog(
            project_id=project_id,
            question=question,
            retrieved_context=context_payload,
            answer=answer,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_by_project(self, project_id: int) -> list[RAGQueryLog]:
        stmt = select(RAGQueryLog).where(RAGQueryLog.project_id == project_id).order_by(RAGQueryLog.id.desc())
        return list(self.db.scalars(stmt).all())
