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

# Куда грузить модель: cpu / cuda / cuda:0 / auto.
# `auto` выбирает cuda при наличии torch.cuda.is_available(), иначе cpu.
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "auto").strip()


def _resolve_device(requested: str) -> str:
    requested = (requested or "auto").strip().lower()
    if requested in ("auto", ""):
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            return "cpu"
        except Exception:  # pragma: no cover — torch может отсутствовать в тестовой среде
            logger.warning("torch недоступен — embedding модель будет грузиться на cpu", exc_info=True)
            return "cpu"
    return requested


_RESOLVED_DEVICE: str | None = None
_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def _log_torch_environment(device: str) -> None:
    """Залогировать, что реально доступно. Помогает диагностировать «всё на CPU»."""
    try:
        import torch

        cuda_ok = torch.cuda.is_available()
        cuda_dev = torch.cuda.device_count() if cuda_ok else 0
        names = [torch.cuda.get_device_name(i) for i in range(cuda_dev)] if cuda_ok else []
        logger.info(
            "Embedding device: requested=%s resolved=%s | torch=%s cuda_available=%s gpus=%d %s",
            EMBEDDING_DEVICE,
            device,
            getattr(torch, "__version__", "?"),
            cuda_ok,
            cuda_dev,
            names,
        )
        if device.startswith("cuda") and not cuda_ok:
            logger.warning(
                "EMBEDDING_DEVICE=%s, но torch.cuda.is_available()=False. "
                "Проверьте, что установлен torch с поддержкой CUDA и проброшен GPU в контейнер "
                "(docker run --gpus all / docker-compose deploy.resources.reservations).",
                EMBEDDING_DEVICE,
            )
    except Exception:  # pragma: no cover
        logger.warning("Не удалось проверить torch/CUDA окружение", exc_info=True)


def _get_model() -> SentenceTransformer:
    global _model, _RESOLVED_DEVICE
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                device = _resolve_device(EMBEDDING_DEVICE)
                _RESOLVED_DEVICE = device
                _log_torch_environment(device)
                logger.info("Loading embedding model %s on device=%s …", MODEL_NAME, device)
                _model = SentenceTransformer(
                    MODEL_NAME,
                    trust_remote_code=True,
                    device=device,
                )
                dim_fn = getattr(_model, "get_embedding_dimension", None) or _model.get_sentence_embedding_dimension
                logger.info("Embedding model loaded – dimension=%d device=%s", dim_fn(), device)
    return _model


def get_active_embedding_device() -> str:
    if _RESOLVED_DEVICE is not None:
        return _RESOLVED_DEVICE
    return _resolve_device(EMBEDDING_DEVICE)


def embed_text(text: str, **_kwargs: object) -> list[float]:
    """Embed a single piece of text using the configured transformer model."""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_texts(texts: list[str], batch_size: int | None = None) -> list[list[float]]:
    """Embed multiple texts in a single batched call (much faster)."""
    model = _get_model()
    bs = batch_size if batch_size is not None else int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=bs)
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
