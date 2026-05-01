from __future__ import annotations

from modules.rag.schemas import RetrievedChunk

MAX_HISTORY_TURNS = 5


def build_rag_prompt(
    *,
    query: str,
    chunks: list[RetrievedChunk],
    history: list[dict] | None = None,
) -> str:
    """
    Build a grounded RAG prompt with:
    - conversation history (for multi-turn context)
    - retrieved context chunks (numbered for ordering only)
    - explicit instructions to stay faithful to the context without leaking retrieval metadata
    """
    sections: list[str] = []

    sections.append(
        "Instructions:\n"
        "- Answer the question using ONLY the provided context.\n"
        "- Do not mention chunk IDs, source IDs, scores, or citation markers like [1] — answer in plain prose.\n"
        "- If the context does not contain enough information, say so explicitly.\n"
        "- Be concise and precise."
    )

    if history:
        recent = history[-MAX_HISTORY_TURNS:]
        history_lines: list[str] = []
        for turn in recent:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            prefix = "User" if role == "user" else "Assistant"
            history_lines.append(f"{prefix}: {content}")
        sections.append("Conversation history:\n" + "\n".join(history_lines))

    if not chunks:
        context_block = "No relevant context was found."
    else:
        context_items: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            header = f"[{idx}]"
            context_items.append(f"{header}\n{chunk.content}")
        context_block = "\n\n".join(context_items)

    sections.append(f"Context:\n{context_block}")
    sections.append(f"Question:\n{query}")

    return "\n\n".join(sections)
