from modules.rag.schemas import RetrieveRequest, RetrieveResponse, RetrievedChunk
from modules.vectordb.schemas import TopKSearchRequest
from modules.vectordb.service import VectorDBService


class VectorRetriever:
    def __init__(self, vectordb: VectorDBService) -> None:
        self.vectordb = vectordb

    def retrieve(self, payload: RetrieveRequest) -> RetrieveResponse:
        result = self.vectordb.search_top_k(
            TopKSearchRequest(
                project_id=payload.project_id,
                query_embedding=payload.query_embedding,
                top_k=payload.top_k,
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
        return RetrieveResponse(items=items)
