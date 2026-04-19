from __future__ import annotations

import re
import unicodedata


_MULTI_NEWLINES = re.compile(r"\n{3,}")
_MULTI_SPACES = re.compile(r"[^\S\n]{2,}")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def clean_text(raw_text: str) -> str:
    """
    Clean raw extracted text while preserving meaningful structure:
    - normalize unicode (NFKC)
    - strip control characters
    - collapse excessive whitespace (but keep single newlines for paragraph boundaries)
    - strip leading/trailing whitespace per line
    """
    text = unicodedata.normalize("NFKC", raw_text)
    text = _CONTROL_CHARS.sub("", text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = _MULTI_NEWLINES.sub("\n\n", text)
    text = _MULTI_SPACES.sub(" ", text)
    return text.strip()
