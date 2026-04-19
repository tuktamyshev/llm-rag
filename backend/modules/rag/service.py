from fastapi import HTTPException, status

from modules.embeddings.service import embed_text
from infrastructure.llm.openrouter import LLMClient
from modules.rag.prompt_builder import build_rag_prompt
from modules.rag.repository import RAGLogRepository
from modules.rag.retriever import VectorRetriever
from modules.rag.schemas import AskRAGRequest, AskRAGResponse, RetrieveRequest


class RAGService:
    def __init__(self, retriever: VectorRetriever, llm_client: LLMClient, logs: RAGLogRepository) -> None:
        self.retriever = retriever
        self.llm_client = llm_client
        self.logs = logs

    def ask(self, payload: AskRAGRequest, history: list[dict] | None = None) -> AskRAGResponse:
        query_embedding = payload.query_embedding or embed_text(payload.query)
        retrieved = self.retriever.retrieve(
            RetrieveRequest(
                project_id=payload.project_id,
                query=payload.query,
                query_embedding=query_embedding,
                top_k=payload.top_k,
            )
        )
        prompt = build_rag_prompt(
            query=payload.query,
            chunks=retrieved.items,
            history=history,
        )
        try:
            answer = self.llm_client.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a precise RAG assistant. "
                    "Answer based on the provided context. "
                    "If the context is insufficient, state it explicitly. "
                    "Keep answers concise and faithful to the context. "
                    "When referencing information, mention the source number."
                ),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        self.logs.create_log(
            project_id=payload.project_id,
            question=payload.query,
            retrieved_context=retrieved.items,
            answer=answer,
        )
        return AskRAGResponse(answer=answer, context_chunks=retrieved.items)
