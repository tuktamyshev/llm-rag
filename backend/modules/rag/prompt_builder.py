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
        "Инструкции к ответу:\n"
        "- Сначала опирайся на контекст ниже. Упоминая факты из него, называй только "
        "читаемое имя источника (строка «Источник» у фрагмента), не раскрывай внутренние ID и не "
        "используй слово «чанк».\n"
        "- Нужен уточняющий ответ или очевидное пояснение, а в контексте этого нет — можно кратко "
        "использовать общие знания; не выдавай за факты из базы то, чего в контексте нет.\n"
        "- Если по сути вопроса в контексте нет достаточных сведений, скажи прямо.\n"
        "- Пиши по существу."
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
        context_block = "Релевантных фрагментов не найдено."
    else:
        context_items: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            name = (chunk.source_title or "").strip() or f"источник #{chunk.source_id}"
            context_items.append(f"[{idx}] Источник: «{name}»\n{chunk.content}")
        context_block = "\n\n".join(context_items)

    sections.append(f"Контекст:\n{context_block}")
    sections.append(f"Вопрос:\n{query}")

    return "\n\n".join(sections)
