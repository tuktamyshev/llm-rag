from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

from modules.rag.schemas import RetrievedChunk

logger = logging.getLogger(__name__)

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

_reranker: CrossEncoder | None = None
_reranker_lock = threading.Lock()


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        with _reranker_lock:
            if _reranker is None:
                from sentence_transformers import CrossEncoder

                logger.info("Loading reranker model %s …", RERANKER_MODEL)
                _reranker = CrossEncoder(RERANKER_MODEL)
                logger.info("Reranker loaded")
    return _reranker


def rerank(query: str, chunks: list[RetrievedChunk], top_n: int | None = None) -> list[RetrievedChunk]:
    """Re-score retrieved chunks using a cross-encoder and return sorted by relevance."""
    if not chunks:
        return []

    reranker = _get_reranker()
    pairs = [(query, chunk.content) for chunk in chunks]
    scores = reranker.predict(pairs)

    scored = list(zip(chunks, scores))
    scored.sort(key=lambda x: float(x[1]), reverse=True)

    limit = top_n if top_n and top_n < len(scored) else len(scored)
    result: list[RetrievedChunk] = []
    for chunk, score in scored[:limit]:
        result.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                content=chunk.content,
                score=float(score),
            )
        )
    return result
