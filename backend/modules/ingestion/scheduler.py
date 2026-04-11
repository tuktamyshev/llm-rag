from datetime import datetime, timedelta


def should_run(cron_expr: str, now: datetime | None = None) -> bool:
    """
    Cron-like stub.
    Supports only patterns like '*/N * * * *'.
    """
    now = now or datetime.utcnow()
    interval = _extract_minute_interval(cron_expr)
    if interval is None:
        return False
    return now.minute % interval == 0


def next_run_at(cron_expr: str, from_dt: datetime | None = None) -> datetime | None:
    """
    Cron-like stub.
    Supports only patterns like '*/N * * * *'.
    """
    from_dt = from_dt or datetime.utcnow()
    interval = _extract_minute_interval(cron_expr)
    if interval is None:
        return None

    candidate = from_dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
    while candidate.minute % interval != 0:
        candidate += timedelta(minutes=1)
    return candidate


def _extract_minute_interval(cron_expr: str) -> int | None:
    parts = cron_expr.split()
    if len(parts) != 5:
        return None
    minute_part = parts[0]
    if not minute_part.startswith("*/"):
        return None
    try:
        value = int(minute_part[2:])
    except ValueError:
        return None
    if value <= 0 or value > 59:
        return None
    return value
