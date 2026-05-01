"""Defaults and helpers for `project.settings['ingestion']`."""

from __future__ import annotations

from datetime import datetime
from typing import Any

DEFAULT_AUTO_REFRESH_INTERVAL_HOURS = 12
DEFAULT_MANUAL_REFRESH_COOLDOWN_SECONDS = 300


def get_ingestion_block(settings: dict[str, Any] | None) -> dict[str, Any]:
    s = settings or {}
    raw = s.get("ingestion")
    return dict(raw) if isinstance(raw, dict) else {}


def auto_refresh_interval_hours(settings: dict[str, Any] | None) -> float:
    ing = get_ingestion_block(settings)
    raw = ing.get("auto_refresh_interval_hours", DEFAULT_AUTO_REFRESH_INTERVAL_HOURS)
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return float(DEFAULT_AUTO_REFRESH_INTERVAL_HOURS)
    if v < 0.25:
        return 0.25
    if v > 8760:
        return 8760.0
    return v


def manual_refresh_cooldown_seconds(settings: dict[str, Any] | None) -> int:
    ing = get_ingestion_block(settings)
    raw = ing.get("manual_refresh_cooldown_seconds", DEFAULT_MANUAL_REFRESH_COOLDOWN_SECONDS)
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_MANUAL_REFRESH_COOLDOWN_SECONDS
    return max(0, min(v, 86400))


def parse_iso_utc(s: str | None) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
