import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db import get_db
from infrastructure.llm.openrouter import OpenRouterLLMClient
from modules.evaluation.schemas import (
    RagasCompareRequest,
    RagasCompareResponse,
    RagasCompareUrlsRequest,
    RagasEvaluateRequest,
    RagasEvaluateResponse,
    RagasModelsPublicResponse,
)
from modules.evaluation.service import (
    build_ragas_models_metadata,
    run_compare_rag_vs_no_rag,
    run_compare_urls,
    run_ragas_from_jsonl,
)
from modules.ingestion.deps import get_ingestion_service
from modules.ingestion.repository import IngestionRepository
from modules.ingestion.service import IngestionService
from modules.projects.repository import ProjectRepository
from modules.projects.service import ProjectService
from modules.rag.repository import RAGLogRepository
from modules.rag.retriever import VectorRetriever
from modules.rag.service import RAGService
from modules.sources.repository import SourceRepository
from modules.users.repository import UserRepository
from modules.vectordb.repository import QdrantRepository, VectorRecordRepository
from modules.vectordb.service import VectorDBService

router = APIRouter()


def _rag_service_for_eval(db: Session = Depends(get_db)) -> RAGService:
    vectordb = VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository())
    return RAGService(
        retriever=VectorRetriever(vectordb=vectordb),
        llm_client=OpenRouterLLMClient(),
        logs=RAGLogRepository(db),
        sources=SourceRepository(db),
        projects=ProjectRepository(db),
    )


@router.get("/ragas-models", response_model=RagasModelsPublicResponse)
def ragas_models_public() -> RagasModelsPublicResponse:
    """Публичные имена моделей для UI (без ключей)."""
    return RagasModelsPublicResponse(models=build_ragas_models_metadata(include_no_rag_llm=True))


@router.post("/ragas", response_model=RagasEvaluateResponse)
def evaluate_ragas(payload: RagasEvaluateRequest) -> RagasEvaluateResponse:
    """
    Запуск метрик RAGAS по JSONL-датасету (вопрос, контексты, эталонный ответ, ответ модели).
    Требует OPENROUTER_API_KEY и установленные пакеты ragas, langchain-openai, langchain-community.
    Операция может занять несколько минут.
    """
    result = run_ragas_from_jsonl(payload.jsonl)
    if result.error and result.samples_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)
    return result


@router.post("/ragas-compare", response_model=RagasCompareResponse)
def compare_ragas_vs_no_rag(
    payload: RagasCompareRequest,
    db: Session = Depends(get_db),
    rag_service: RAGService = Depends(_rag_service_for_eval),
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> RagasCompareResponse:
    """
    RAGAS: для каждой строки JSONL — временный проект (индексация contexts), RAG (retrieval + LLM), удаление проекта;
    ответ без RAG (прямой LLM). Метрики к ground_truth. В JSONL: question, ground_truth, contexts (непустой список).
    """
    eval_user_id = int(os.environ.get("RAGAS_COMPARE_USER_ID", "1"))
    source_repo = SourceRepository(db)
    project_service = ProjectService(
        projects=ProjectRepository(db),
        users=UserRepository(db),
        sources=source_repo,
        ingestion=IngestionRepository(db),
        vectordb=VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository()),
    )
    result = run_compare_rag_vs_no_rag(
        payload.jsonl,
        top_k=payload.top_k,
        rag_service=rag_service,
        ingestion=ingestion,
        project_service=project_service,
        sources=source_repo,
        users=UserRepository(db),
        eval_user_id=eval_user_id,
    )
    if result.error and result.samples_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)
    return result


@router.post("/ragas-compare-urls", response_model=RagasCompareResponse)
def compare_ragas_urls(
    payload: RagasCompareUrlsRequest,
    db: Session = Depends(get_db),
    rag_service: RAGService = Depends(_rag_service_for_eval),
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> RagasCompareResponse:
    """
    Сравнение RAGAS на «живых» URL.

    Сервер скачивает каждую ссылку как обычный WEB‑источник, поднимает ДВА временных проекта
    (standard + raw), индексирует все URL в каждый проект, затем для каждого вопроса из JSONL
    выполняет RAG. Параллельно строится ветка «без RAG». Все временные проекты удаляются.
    """
    eval_user_id = int(os.environ.get("RAGAS_COMPARE_USER_ID", "1"))
    source_repo = SourceRepository(db)
    project_service = ProjectService(
        projects=ProjectRepository(db),
        users=UserRepository(db),
        sources=source_repo,
        ingestion=IngestionRepository(db),
        vectordb=VectorDBService(records=VectorRecordRepository(db), qdrant=QdrantRepository()),
    )
    result = run_compare_urls(
        payload.jsonl,
        urls=payload.urls,
        top_k=payload.top_k,
        rag_service=rag_service,
        ingestion=ingestion,
        project_service=project_service,
        sources=source_repo,
        users=UserRepository(db),
        eval_user_id=eval_user_id,
    )
    if result.error and result.samples_count == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)
    return result
