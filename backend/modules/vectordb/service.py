from fastapi import HTTPException, status

from modules.vectordb.repository import QdrantRepository, VectorRecordRepository
from modules.vectordb.schemas import TopKSearchRequest, TopKSearchResponse, UpsertEmbeddingsRequest


class VectorDBService:
    def __init__(self, records: VectorRecordRepository, qdrant: QdrantRepository) -> None:
        self.records = records
        self.qdrant = qdrant

    def delete_embeddings_for_chunk_ids(self, chunk_ids: list[int]) -> None:
        """Drop Qdrant points keyed by chunk id before replacing chunks in PostgreSQL."""
        if not chunk_ids:
            return
        self.qdrant.delete_points_by_ids(chunk_ids)

    def upsert_embeddings(self, payload: UpsertEmbeddingsRequest) -> dict:
        vector_size = len(payload.points[0].embedding)
        if any(len(point.embedding) != vector_size for point in payload.points):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All embeddings must have the same vector size",
            )

        points_for_qdrant: list[dict] = []
        for point in payload.points:
            points_for_qdrant.append(
                {
                    "point_id": point.chunk_id,
                    "embedding": point.embedding,
                    "payload": {
                        "chunk_id": point.chunk_id,
                        "source_id": point.source_id,
                        "project_id": point.project_id,
                        "content": point.content,
                    },
                }
            )

        self.qdrant.upsert_points(points_for_qdrant, vector_size=vector_size)

        for point in payload.points:
            self.records.upsert(
                chunk_id=point.chunk_id,
                point_id=str(point.chunk_id),
                collection_name=self.qdrant.collection_name,
                commit=False,
            )
        self.records.commit()

        return {
            "upserted": len(payload.points),
            "collection_name": self.qdrant.collection_name,
            "vector_size": vector_size,
        }

    def search_top_k(self, payload: TopKSearchRequest) -> TopKSearchResponse:
        items = self.qdrant.search_top_k(
            project_id=payload.project_id,
            query_embedding=payload.query_embedding,
            top_k=payload.top_k,
        )
        return TopKSearchResponse(collection_name=self.qdrant.collection_name, items=items)
