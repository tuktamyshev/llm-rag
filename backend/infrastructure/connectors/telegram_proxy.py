"""
Опциональный прокси и параметры устойчивости для Telethon.

Переменная TELEGRAM_PROXY — URL вида:
  socks5://127.0.0.1:1080
  socks5://user:pass@127.0.0.1:1080
  http://127.0.0.1:8080

Если Telegram «не коннектится» из Docker / корпоративной сети — поднимите VPN или локальный SOCKS
на хосте и пробросьте порт в контейнер или укажите адрес прокси из compose.
"""

from __future__ import annotations

import logging
import os
from urllib.parse import unquote, urlparse

logger = logging.getLogger(__name__)


def telethon_client_kwargs() -> dict:
    """Аргументы для TelegramClient(..., **kwargs)."""
    kw: dict = {
        "connection_retries": int(os.getenv("TELEGRAM_CONNECTION_RETRIES", "15")),
        "timeout": int(os.getenv("TELEGRAM_TIMEOUT_SEC", "25")),
        "request_retries": int(os.getenv("TELEGRAM_REQUEST_RETRIES", "5")),
        "retry_delay": int(os.getenv("TELEGRAM_RETRY_DELAY_SEC", "2")),
        "use_ipv6": os.getenv("TELEGRAM_USE_IPV6", "").strip().lower() in ("1", "true", "yes"),
    }
    proxy = _proxy_tuple_from_env()
    if proxy is not None:
        kw["proxy"] = proxy
    return kw


def _proxy_tuple_from_env() -> tuple | None:
    raw = os.getenv("TELEGRAM_PROXY", "").strip()
    if not raw:
        return None

    try:
        import socks
    except ImportError:
        logger.warning("PySocks не установлен — TELEGRAM_PROXY игнорируется (pip install PySocks)")
        return None

    u = urlparse(raw)
    host = u.hostname
    if not host:
        logger.warning("TELEGRAM_PROXY: не указан хост в URL")
        return None

    scheme = (u.scheme or "").lower()
    port = u.port
    user = unquote(u.username) if u.username else None
    pwd = unquote(u.password) if u.password else None
    rdns = True

    if scheme == "socks5":
        typ = socks.SOCKS5
        if port is None:
            port = 1080
    elif scheme == "socks4":
        typ = socks.SOCKS4
        if port is None:
            port = 1080
    elif scheme in ("http", "https"):
        typ = socks.HTTP
        if port is None:
            port = 8080
    else:
        logger.warning("TELEGRAM_PROXY: неподдерживаемая схема %s (ожидаются socks5, socks4, http)", scheme)
        return None

    if user and pwd:
        return (typ, host, port, rdns, user, pwd)
    return (typ, host, port, rdns)
