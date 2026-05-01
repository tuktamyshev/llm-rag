from fastapi import HTTPException, status

from modules.embeddings.service import embed_text
from infrastructure.llm.openrouter import LLMClient
from modules.rag.default_system_prompt import build_combined_system_prompt
from modules.rag.prompt_builder import build_rag_prompt
from modules.rag.repository import RAGLogRepository
from modules.rag.retriever import VectorRetriever
from modules.rag.schemas import AskRAGRequest, AskRAGResponse, RetrieveRequest, RetrievedChunk
from modules.projects.repository import ProjectRepository
from modules.sources.repository import SourceRepository


class RAGService:
    def __init__(
        self,
        retriever: VectorRetriever,
        llm_client: LLMClient,
        logs: RAGLogRepository,
        sources: SourceRepository,
        projects: ProjectRepository,
    ) -> None:
        self.retriever = retriever
        self.llm_client = llm_client
        self.logs = logs
        self.sources = sources
        self.projects = projects

    def ask(
        self,
        payload: AskRAGRequest,
        history: list[dict] | None = None,
        *,
        project_prompt: str | None = None,
    ) -> AskRAGResponse:
        pp = project_prompt
        if pp is None:
            proj = self.projects.get_by_id(payload.project_id)
            pp = proj.prompt if proj else None

        query_embedding = payload.query_embedding or embed_text(payload.query)
        retrieved = self.retriever.retrieve(
            RetrieveRequest(
                project_id=payload.project_id,
                query=payload.query,
                query_embedding=query_embedding,
                top_k=payload.top_k,
            )
        )
        enriched = self._attach_source_titles(retrieved.items)
        prompt = build_rag_prompt(
            query=payload.query,
            chunks=enriched,
            history=history,
        )
        try:
            answer = self.llm_client.generate(
                prompt=prompt,
                system_prompt=build_combined_system_prompt(project_prompt=pp),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        self.logs.create_log(
            project_id=payload.project_id,
            question=payload.query,
            retrieved_context=enriched,
            answer=answer,
        )
        return AskRAGResponse(answer=answer, context_chunks=enriched)

    def _attach_source_titles(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        ids = list({c.source_id for c in chunks})
        titles = self.sources.titles_for_source_ids(ids)
        out: list[RetrievedChunk] = []
        for c in chunks:
            title = titles.get(c.source_id, "")
            out.append(
                RetrievedChunk(
                    chunk_id=c.chunk_id,
                    source_id=c.source_id,
                    content=c.content,
                    score=c.score,
                    source_title=title,
                )
            )
        return out
