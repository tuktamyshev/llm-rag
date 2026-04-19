from __future__ import annotations

import os

from modules.rag.reranker import rerank
from modules.rag.schemas import RetrieveRequest, RetrieveResponse, RetrievedChunk
from modules.vectordb.schemas import TopKSearchRequest
from modules.vectordb.service import VectorDBService

RERANK_ENABLED = os.getenv("RERANK_ENABLED", "true").lower() in ("1", "true", "yes")
RERANK_FETCH_MULTIPLIER = int(os.getenv("RERANK_FETCH_MULTIPLIER", "3"))


class VectorRetriever:
    def __init__(self, vectordb: VectorDBService) -> None:
        self.vectordb = vectordb

    def retrieve(self, payload: RetrieveRequest) -> RetrieveResponse:
        fetch_k = payload.top_k * RERANK_FETCH_MULTIPLIER if RERANK_ENABLED else payload.top_k

        result = self.vectordb.search_top_k(
            TopKSearchRequest(
                project_id=payload.project_id,
                query_embedding=payload.query_embedding,
                top_k=fetch_k,
            )
        )
        items = [
            RetrievedChunk(
                chunk_id=item.chunk_id,
                source_id=item.source_id,
                content=item.content,
                score=item.score,
            )
            for item in result.items
        ]

        if RERANK_ENABLED and items:
            items = rerank(
                query=payload.query,
                chunks=items,
                top_n=payload.top_k,
            )

        return RetrieveResponse(items=items)
