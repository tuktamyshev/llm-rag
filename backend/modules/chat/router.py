from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from infrastructure.llm.openrouter import OpenRouterLLMClient
from modules.chat.repository import ChatRepository
from modules.chat.schemas import ChatLogRead, ChatRequest, ChatResponse
from modules.chat.service import ChatService
from modules.rag.repository import RAGLogRepository
from modules.rag.retriever import VectorRetriever
from modules.rag.service import RAGService
from modules.vectordb.repository import QdrantRepository, VectorRecordRepository
from modules.vectordb.service import VectorDBService


router = APIRouter()


def _chat_repo(db: Session = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)


def _chat_service(db: Session = Depends(get_db)) -> ChatService:
    vectordb = VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository())
    rag_service = RAGService(
        retriever=VectorRetriever(vectordb=vectordb),
        llm_client=OpenRouterLLMClient(),
        logs=RAGLogRepository(db),
    )
    return ChatService(rag_service=rag_service, repository=ChatRepository(db))


@router.get("/{project_id}/history", response_model=list[ChatLogRead])
def chat_history(
    project_id: int, limit: int = 100, repo: ChatRepository = Depends(_chat_repo)
) -> list[ChatLogRead]:
    logs = repo.list_by_project(project_id, limit=limit)
    return [ChatLogRead.model_validate(log) for log in logs]


@router.post("/{project_id}", response_model=ChatResponse)
def chat(project_id: int, payload: ChatRequest, service: ChatService = Depends(_chat_service)) -> ChatResponse:
    return service.chat(project_id=project_id, payload=payload)
