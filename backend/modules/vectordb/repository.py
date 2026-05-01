import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.vectordb.models import VectorRecord


try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, Filter, FieldCondition, MatchValue, PointStruct, VectorParams
except ImportError:  # pragma: no cover
    QdrantClient = None  # type: ignore[assignment]
    Distance = Filter = FieldCondition = MatchValue = PointStruct = VectorParams = None  # type: ignore[assignment]


class VectorRecordRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(
        self,
        chunk_id: int,
        point_id: str,
        collection_name: str,
        *,
        commit: bool = True,
    ) -> VectorRecord:
        stmt = select(VectorRecord).where(VectorRecord.chunk_id == chunk_id)
        record = self.db.scalar(stmt)
        if record:
            record.point_id = point_id
            record.collection_name = collection_name
        else:
            record = VectorRecord(chunk_id=chunk_id, point_id=point_id, collection_name=collection_name)
            self.db.add(record)
        if commit:
            self.db.commit()
            self.db.refresh(record)
        else:
            self.db.flush()
            self.db.refresh(record)
        return record

    def commit(self) -> None:
        self.db.commit()


class QdrantRepository:
    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        collection_name: str = "source_chunks",
    ) -> None:
        if QdrantClient is None:
            raise RuntimeError("qdrant-client is required for vectordb module")
        qdrant_host = host or os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = port or int(os.getenv("QDRANT_PORT", "6333"))
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = collection_name

    def ensure_collection(self, vector_size: int) -> None:
        if self.client.collection_exists(self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert_points(self, points: list[dict], vector_size: int) -> None:
        self.ensure_collection(vector_size=vector_size)
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(id=int(point["point_id"]), vector=point["embedding"], payload=point["payload"])
                for point in points
            ],
        )

    def delete_points_by_ids(self, point_ids: list[int]) -> None:
        """Remove vectors so re-ingestion does not leave stale duplicates in Qdrant."""
        if not point_ids or not self.client.collection_exists(self.collection_name):
            return
        from qdrant_client.http.models import PointIdsList

        self.client.delete(collection_name=self.collection_name, points_selector=PointIdsList(points=point_ids))

    def search_top_k(self, *, project_id: int, query_embedding: list[float], top_k: int) -> list[dict]:
        if not self.client.collection_exists(self.collection_name):
            return []

        query_filter = Filter(must=[FieldCondition(key="project_id", match=MatchValue(value=project_id))])
        result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter,
        )
        items: list[dict] = []
        for point in result:
            payload = point.payload or {}
            items.append(
                {
                    "chunk_id": int(payload.get("chunk_id", 0)),
                    "source_id": int(payload.get("source_id", 0)),
                    "project_id": int(payload.get("project_id", 0)),
                    "content": str(payload.get("content", "")),
                    "score": float(point.score),
                }
            )
        return items
