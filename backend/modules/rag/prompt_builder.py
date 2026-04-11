from modules.rag.schemas import RetrievedChunk


def build_rag_prompt(*, query: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        context_block = "No relevant context was found."
    else:
        context_items = []
        for idx, chunk in enumerate(chunks, start=1):
            context_items.append(
                f"[{idx}] source_id={chunk.source_id} chunk_id={chunk.chunk_id} score={chunk.score:.4f}\n{chunk.content}"
            )
        context_block = "\n\n".join(context_items)

    return (
        "Use only the context below to answer the question.\n"
        "If the context is insufficient, state it explicitly.\n\n"
        f"Question:\n{query}\n\n"
        f"Context:\n{context_block}"
    )
