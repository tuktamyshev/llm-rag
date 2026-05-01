"""Persist uploaded files for FILE-type sources."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

MAX_FILE_BYTES = 15 * 1024 * 1024


def get_upload_root() -> Path:
    raw = os.getenv("UPLOAD_DIR", "uploads")
    p = Path(raw)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def safe_original_name(name: str) -> str:
    base = os.path.basename(name or "upload")
    cleaned = re.sub(r"[^\w.\-\s]", "_", base).strip()
    return (cleaned or "upload")[:200]


def store_project_file(project_id: int, original_filename: str, data: bytes) -> tuple[str, Path]:
    """Save bytes under upload root. Returns (relative path from root, absolute path)."""
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"File too large (max {MAX_FILE_BYTES} bytes)")

    rel_dir = f"project_{project_id}"
    stem = f"{uuid.uuid4().hex}_{safe_original_name(original_filename)}"
    root = get_upload_root()
    dest_dir = root / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / stem
    dest.write_bytes(data)
    relpath = f"{rel_dir}/{stem}"
    return relpath, dest


def resolve_stored_file(relpath: str) -> Path:
    """Resolve a stored relative path; rejects traversal."""
    if not relpath or relpath.startswith(("/", "\\")):
        raise ValueError("Invalid stored path")
    parts = Path(relpath).parts
    if ".." in parts:
        raise ValueError("Invalid stored path")

    root = get_upload_root()
    path = (root / relpath).resolve()
    root_r = root.resolve()
    try:
        path.relative_to(root_r)
    except ValueError as exc:
        raise ValueError("Invalid stored path") from exc
    return path


def delete_stored_file_if_exists(relpath: str | None) -> None:
    if not relpath:
        return
    try:
        path = resolve_stored_file(relpath)
    except ValueError:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
