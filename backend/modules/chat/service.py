from modules.chat.repository import ChatRepository
from modules.chat.schemas import ChatRequest, ChatResponse
from modules.rag.schemas import AskRAGRequest
from modules.rag.service import RAGService


class ChatService:
    def __init__(self, rag_service: RAGService, repository: ChatRepository) -> None:
        self.rag_service = rag_service
        self.repository = repository

    def chat(self, project_id: int, payload: ChatRequest) -> ChatResponse:
        rag_response = self.rag_service.ask(
            AskRAGRequest(
                project_id=project_id,
                query=payload.message,
                query_embedding=payload.query_embedding,
                top_k=payload.top_k,
            )
        )
        sources = [
            f"source_id={chunk.source_id}, chunk_id={chunk.chunk_id}, score={chunk.score:.4f}"
            for chunk in rag_response.context_chunks
        ]
        self.repository.create_log(
            project_id=project_id,
            question=payload.message,
            answer=rag_response.answer,
            sources=sources,
        )
        return ChatResponse(answer=rag_response.answer, sources=sources)
