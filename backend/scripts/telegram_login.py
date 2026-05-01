#!/usr/bin/env python3
"""
Одноразовый интерактивный вход Telethon (код из Telegram / пароль 2FA).
Сохраняет сессию в TELEGRAM_SESSION_DIR — тот же каталог, что у backend в Docker.

Запуск из корня llm-rag (рядом с docker-compose.yml), с заполненным .env:

  docker compose run --rm -it backend python scripts/telegram_login.py

или:  make telegram-login
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Запуск как file://…/scripts/telegram_login.py не кладёт /app/backend в sys.path
_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))


async def _main() -> None:
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    session_name = os.getenv("TELEGRAM_SESSION_NAME", "llm_rag_session")
    session_dir = os.getenv("TELEGRAM_SESSION_DIR", "/data/telegram_session")

    if not api_id or not api_hash:
        print(
            "Задайте TELEGRAM_API_ID и TELEGRAM_API_HASH в .env "
            "(https://my.telegram.org → API development tools).",
            file=sys.stderr,
        )
        sys.exit(1)

    os.makedirs(session_dir, exist_ok=True)
    session_path = os.path.join(session_dir, session_name)

    from infrastructure.connectors.telegram_proxy import telethon_client_kwargs
    from telethon import TelegramClient

    client = TelegramClient(session_path, int(api_id), api_hash, **telethon_client_kwargs())
    await client.start()
    me = await client.get_me()
    print(f"Вход выполнен: @{me.username}" if me.username else f"Вход выполнен: id={me.id}")
    await client.disconnect()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
