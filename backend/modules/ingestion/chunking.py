from __future__ import annotations

import re

_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]


def naive_chunk_text(text: str, chunk_size: int = 1000) -> list[str]:
    """
    Простое окно фиксированной длины без оверлапа и без учёта разделителей —
    «raw» вариант для сравнения с осмысленным `chunk_text`.
    """
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size) if text[i : i + chunk_size]]


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
    separators: list[str] | None = None,
) -> list[str]:
    """
    Recursive character text splitter that tries to keep semantically
    coherent blocks together by splitting on the highest-priority
    separator first, then falling back to smaller separators.
    """
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    seps = separators if separators is not None else list(_SEPARATORS)
    return _recursive_split(text, chunk_size, overlap, seps)


def _recursive_split(
    text: str,
    chunk_size: int,
    overlap: int,
    separators: list[str],
) -> list[str]:
    if len(text) <= chunk_size:
        stripped = text.strip()
        return [stripped] if stripped else []

    sep = separators[0] if separators else ""
    remaining_seps = separators[1:] if len(separators) > 1 else []

    if sep:
        parts = text.split(sep)
    else:
        parts = list(text)

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for part in parts:
        part_len = len(part) + (len(sep) if current else 0)

        if current_len + part_len > chunk_size and current:
            merged = sep.join(current)
            if len(merged) > chunk_size and remaining_seps:
                chunks.extend(_recursive_split(merged, chunk_size, overlap, remaining_seps))
            else:
                stripped = merged.strip()
                if stripped:
                    chunks.append(stripped)

            overlap_parts = _build_overlap(current, sep, overlap)
            current = overlap_parts
            current_len = sum(len(p) for p in current) + len(sep) * max(0, len(current) - 1)

        current.append(part)
        current_len += part_len

    if current:
        merged = sep.join(current)
        if len(merged) > chunk_size and remaining_seps:
            chunks.extend(_recursive_split(merged, chunk_size, overlap, remaining_seps))
        else:
            stripped = merged.strip()
            if stripped:
                chunks.append(stripped)

    return chunks


def _build_overlap(parts: list[str], sep: str, overlap: int) -> list[str]:
    """Take trailing parts whose combined length fits within *overlap*."""
    result: list[str] = []
    total = 0
    for part in reversed(parts):
        addition = len(part) + (len(sep) if result else 0)
        if total + addition > overlap:
            break
        result.insert(0, part)
        total += addition
    return result


def split_sentences(text: str) -> list[str]:
    """Split text into sentences (utility for metrics / evaluation)."""
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in parts if s.strip()]
