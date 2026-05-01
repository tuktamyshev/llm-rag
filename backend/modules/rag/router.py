from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from infrastructure.llm.openrouter import OpenRouterLLMClient
from modules.projects.repository import ProjectRepository
from modules.rag.repository import RAGLogRepository
from modules.rag.retriever import VectorRetriever
from modules.rag.schemas import AskRAGRequest, AskRAGResponse, RetrieveRequest, RetrieveResponse
from modules.rag.service import RAGService
from modules.sources.repository import SourceRepository
from modules.vectordb.repository import QdrantRepository, VectorRecordRepository
from modules.vectordb.service import VectorDBService


router = APIRouter()


def _vectordb_service(db: Session = Depends(get_db)) -> VectorDBService:
    return VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository())


def _rag_service(
    db: Session = Depends(get_db), vectordb: VectorDBService = Depends(_vectordb_service)
) -> RAGService:
    retriever = VectorRetriever(vectordb=vectordb)
    llm_client = OpenRouterLLMClient()
    logs = RAGLogRepository(db)
    return RAGService(
        retriever=retriever,
        llm_client=llm_client,
        logs=logs,
        sources=SourceRepository(db),
        projects=ProjectRepository(db),
    )


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(payload: RetrieveRequest, vectordb: VectorDBService = Depends(_vectordb_service)) -> RetrieveResponse:
    return VectorRetriever(vectordb=vectordb).retrieve(payload)


@router.post("/ask", response_model=AskRAGResponse)
def ask(payload: AskRAGRequest, service: RAGService = Depends(_rag_service)) -> AskRAGResponse:
    return service.ask(payload)
