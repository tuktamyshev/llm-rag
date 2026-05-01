#!/usr/bin/env python3
"""
Проверка доступа к Telegram из того же окружения, что у backend (Telethon + TELEGRAM_PROXY).

Запуск из каталога llm-rag:
  docker compose run --rm backend python /app/backend/scripts/telegram_check.py

или:  make telegram-check
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))


async def _main() -> int:
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    session_name = os.getenv("TELEGRAM_SESSION_NAME", "llm_rag_session")
    session_dir = os.getenv("TELEGRAM_SESSION_DIR", "/data/telegram_session")

    if not api_id or not api_hash:
        print("Задайте TELEGRAM_API_ID и TELEGRAM_API_HASH в .env", file=sys.stderr)
        return 1

    from infrastructure.connectors.telegram_proxy import telethon_client_kwargs
    from telethon import TelegramClient

    os.makedirs(session_dir, exist_ok=True)
    session_path = os.path.join(session_dir, session_name)

    client = TelegramClient(
        session_path,
        int(api_id),
        api_hash,
        **telethon_client_kwargs(),
    )

    print("Подключение к дата-центрам Telegram…")
    try:
        await client.connect()
    except Exception as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2

    if not client.is_connected():
        print("Не удалось установить соединение.", file=sys.stderr)
        return 2

    print("OK: TCP/TLS до Telegram работает (Telethon подключился).")

    if await client.is_user_authorized():
        me = await client.get_me()
        uname = f"@{me.username}" if me.username else f"id={me.id}"
        print(f"Сессия авторизована: {uname}")
    else:
        print("Сессия ещё не создана — выполните: make telegram-login")

    await client.disconnect()
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
