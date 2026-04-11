from modules.embeddings.repository import EmbeddingRepository
from modules.embeddings.schemas import EmbeddedChunk


MODEL_NAME = "stub-hash-32"


def embed_text(text: str, size: int = 32) -> list[float]:
    """
    Lightweight deterministic embedding stub for local/demo flow.
    Replace with real model-backed embeddings in production.
    """
    vector = [0.0] * size
    normalized = text.strip().lower()
    for idx, char in enumerate(normalized):
        vector[idx % size] += float(ord(char))

    norm = sum(value * value for value in vector) ** 0.5
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class EmbeddingService:
    def __init__(self, repository: EmbeddingRepository) -> None:
        self.repository = repository

    def embed_and_track_chunks(self, chunks: list[dict], size: int = 32) -> list[EmbeddedChunk]:
        items: list[EmbeddedChunk] = []
        for chunk in chunks:
            vector = embed_text(chunk["content"], size=size)
            self.repository.upsert_record(
                chunk_id=chunk["chunk_id"],
                model_name=MODEL_NAME,
                vector_size=len(vector),
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
        return items
