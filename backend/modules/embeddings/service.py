from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING

from modules.embeddings.schemas import EmbeddedChunk

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

    from modules.embeddings.repository import EmbeddingRepository

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "ai-sage/Giga-Embeddings-instruct")

_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model %s …", MODEL_NAME)
                _model = SentenceTransformer(MODEL_NAME, trust_remote_code=True)
                dim_fn = getattr(_model, "get_embedding_dimension", None) or _model.get_sentence_embedding_dimension
                logger.info("Model loaded – dimension=%d", dim_fn())
    return _model


def embed_text(text: str, **_kwargs: object) -> list[float]:
    """Embed a single piece of text using the configured transformer model."""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Embed multiple texts in a single batched call (much faster)."""
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=batch_size)
    return vectors.tolist()


def get_vector_size() -> int:
    model = _get_model()
    dim_fn = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
    return dim_fn()


class EmbeddingService:
    def __init__(self, repository: EmbeddingRepository) -> None:
        self.repository = repository

    def embed_and_track_chunks(self, chunks: list[dict], **_kwargs: object) -> list[EmbeddedChunk]:
        if not chunks:
            return []

        contents = [c["content"] for c in chunks]
        vectors = embed_texts(contents)
        vector_size = len(vectors[0])

        items: list[EmbeddedChunk] = []
        for chunk, vector in zip(chunks, vectors):
            self.repository.upsert_record(
                chunk_id=chunk["chunk_id"],
                model_name=MODEL_NAME,
                vector_size=vector_size,
                commit=False,
            )
            items.append(
                EmbeddedChunk(
                    chunk_id=chunk["chunk_id"],
                    source_id=chunk["source_id"],
                    project_id=chunk["project_id"],
                    content=chunk["content"],
                    embedding=vector,
                )
            )
        self.repository.commit()
        return items
