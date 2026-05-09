"""
Real Telegram integration using Telethon.

Fetches message history from channels / groups / chats by chat_id or @username.
Requires TELEGRAM_API_ID and TELEGRAM_API_HASH from https://my.telegram.org.

Авторизация выполняется ОТДЕЛЬНО (`make telegram-login`) и сохраняется в volume
TELEGRAM_SESSION_DIR. Здесь мы только подключаемся существующей сессией —
никакого интерактивного ввода телефона/кода в production-пайплайне.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from infrastructure.connectors.telegram_proxy import telethon_client_kwargs

logger = logging.getLogger(__name__)


class TelegramFetchError(Exception):
    """Telegram недоступен или сообщения не получены — не индексировать как текст чанков.

    Не наследуем RuntimeError: в fetch_telegram_messages есть `except RuntimeError` для
    переключения на asyncio.run — иначе ошибки Telegram ошибочно перехватывались бы там.
    """


TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION_NAME", "llm_rag_session")
TELEGRAM_MESSAGE_LIMIT = int(os.getenv("TELEGRAM_MESSAGE_LIMIT", "200"))
TELEGRAM_DAYS_BACK = int(os.getenv("TELEGRAM_DAYS_BACK", "30"))


def _session_path() -> str:
    return os.path.join(
        os.getenv("TELEGRAM_SESSION_DIR", "/tmp"),
        TELEGRAM_SESSION,
    )


def fetch_telegram_messages(chat_id: str, title: str) -> str:
    """
    Synchronous wrapper around the async Telethon client.
    Безопасен и из sync (фоновый ингест), и из async-контекста (FastAPI handler).
    Никогда не использует deprecated `asyncio.get_event_loop()`.
    """
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        logger.warning(
            "TELEGRAM_API_ID / TELEGRAM_API_HASH not set — cannot fetch Telegram for '%s'.",
            title,
        )
        raise TelegramFetchError(
            "Telegram не настроен: задайте TELEGRAM_API_ID и TELEGRAM_API_HASH "
            "(https://my.telegram.org) и перезапустите backend."
        )

    if _running_inside_event_loop():
        result_box: dict[str, Any] = {}

        def _runner() -> None:
            try:
                result_box["value"] = asyncio.run(_async_fetch_messages(chat_id, title))
            except BaseException as exc:  # noqa: BLE001 — пробрасываем в основной поток
                result_box["error"] = exc

        thread = threading.Thread(target=_runner, daemon=True, name="telegram-fetch")
        thread.start()
        thread.join()
        if "error" in result_box:
            raise result_box["error"]
        return str(result_box.get("value", ""))

    return asyncio.run(_async_fetch_messages(chat_id, title))


def _running_inside_event_loop() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


async def _async_fetch_messages(chat_id: str, title: str) -> str:
    """Fetch messages from a Telegram channel/chat using Telethon."""
    try:
        from telethon import TelegramClient, errors  # noqa: F401 — errors используется ниже
    except ImportError:
        logger.error("telethon is not installed — pip install telethon")
        raise TelegramFetchError(
            "Пакет telethon не установлен (pip install telethon)."
        ) from None

    session_path = _session_path()
    os.makedirs(os.path.dirname(session_path), exist_ok=True)

    client = TelegramClient(
        session_path,
        int(TELEGRAM_API_ID),
        TELEGRAM_API_HASH,
        **telethon_client_kwargs(),
    )

    try:
        try:
            await client.connect()
        except OSError as exc:
            raise TelegramFetchError(
                f"Не удаётся подключиться к Telegram: {exc}. "
                "Проверьте сеть/файрвол или задайте TELEGRAM_PROXY (socks5://…)."
            ) from exc

        if not client.is_connected():
            raise TelegramFetchError(
                "Telethon не смог установить соединение с дата-центром Telegram."
            )

        if not await client.is_user_authorized():
            raise TelegramFetchError(
                "Telegram-сессия не авторизована. Выполните одноразовый вход: "
                "`make telegram-login` (или `docker compose run --rm -it backend "
                "python /app/backend/scripts/telegram_login.py`)."
            )

        entity = await _resolve_entity(client, chat_id)
        if entity is None:
            raise TelegramFetchError(f"Не удалось найти чат или канал: {chat_id}")

        offset_date = datetime.now(timezone.utc) - timedelta(days=TELEGRAM_DAYS_BACK)
        raw_messages: list[dict] = []

        try:
            async for msg in client.iter_messages(
                entity,
                limit=TELEGRAM_MESSAGE_LIMIT,
                offset_date=offset_date,
                reverse=True,
            ):
                if not getattr(msg, "text", None):
                    continue
                raw_messages.append(
                    {
                        "id": msg.id,
                        "date": msg.date.isoformat() if msg.date else "",
                        "text": msg.text,
                        "views": getattr(msg, "views", None),
                    }
                )
        except errors.FloodWaitError as exc:
            raise TelegramFetchError(
                f"Telegram FloodWait: подождите {exc.seconds} с и повторите запрос."
            ) from exc
        except errors.ChannelPrivateError as exc:
            raise TelegramFetchError(
                f"Канал/чат «{chat_id}» закрыт или недоступен этому аккаунту."
            ) from exc
        except errors.ChatAdminRequiredError as exc:
            raise TelegramFetchError(
                f"Для чтения «{chat_id}» нужны права админа этому аккаунту."
            ) from exc

        if not raw_messages:
            raise TelegramFetchError(
                f"Нет текстовых сообщений в «{title}» за последние {TELEGRAM_DAYS_BACK} дн. "
                "(проверьте chat_id, доступ аккаунта и при необходимости TELEGRAM_DAYS_BACK)."
            )

        blocks = _group_messages_into_blocks(raw_messages, title)
        logger.info(
            "Fetched %d messages from '%s', grouped into %d blocks",
            len(raw_messages),
            title,
            len(blocks),
        )
        return "\n\n".join(blocks)

    except TelegramFetchError:
        raise
    except Exception as exc:
        logger.exception("Telegram fetch error for '%s'", title)
        raise TelegramFetchError(str(exc)) from exc
    finally:
        try:
            await client.disconnect()
        except Exception:
            logger.debug("Telethon disconnect raised", exc_info=True)


async def _resolve_entity(client, chat_id: str):
    """Try to resolve chat by numeric ID, @username, or invite link."""
    from telethon import errors

    if chat_id.startswith("https://t.me/"):
        chat_id = chat_id.replace("https://t.me/", "@")

    try:
        if chat_id.lstrip("-").isdigit():
            return await client.get_entity(int(chat_id))
        return await client.get_entity(chat_id)
    except (errors.UsernameNotOccupiedError, errors.UsernameInvalidError, ValueError) as exc:
        logger.warning("Could not resolve entity '%s': %s", chat_id, exc)
        return None


def _group_messages_into_blocks(
    messages: list[dict],
    title: str,
    max_gap_minutes: int = 60,
) -> list[str]:
    """
    Group messages into temporal blocks.
    Messages within max_gap_minutes of each other are merged into one block.
    """
    if not messages:
        return []

    blocks: list[str] = []
    current_block: list[str] = []
    prev_date: datetime | None = None

    for msg in messages:
        msg_date = None
        if msg["date"]:
            try:
                msg_date = datetime.fromisoformat(msg["date"])
            except ValueError:
                pass

        if prev_date and msg_date:
            gap = (msg_date - prev_date).total_seconds() / 60
            if gap > max_gap_minutes and current_block:
                blocks.append("\n".join(current_block))
                current_block = []

        date_str = msg["date"][:10] if msg["date"] else ""
        line = f"[{date_str}] {msg['text']}" if date_str else msg["text"]
        current_block.append(line)
        prev_date = msg_date

    if current_block:
        blocks.append("\n".join(current_block))

    return blocks
