from sqlalchemy.orm import Session

from modules.chat.models import ChatLog


class ChatRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_log(self, *, project_id: int, question: str, answer: str, sources: list[str]) -> ChatLog:
        log = ChatLog(project_id=project_id, question=question, answer=answer, sources=sources)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_by_project(self, project_id: int, *, limit: int = 100) -> list[ChatLog]:
        return (
            self.db.query(ChatLog)
            .filter(ChatLog.project_id == project_id)
            .order_by(ChatLog.created_at.asc())
            .limit(limit)
            .all()
        )
