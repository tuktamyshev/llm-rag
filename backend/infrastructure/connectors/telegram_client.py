"""
Real Telegram integration using Telethon.

Fetches message history from channels / groups / chats by chat_id or @username.
Requires TELEGRAM_API_ID and TELEGRAM_API_HASH from https://my.telegram.org.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION = os.getenv("TELEGRAM_SESSION_NAME", "llm_rag_session")
TELEGRAM_MESSAGE_LIMIT = int(os.getenv("TELEGRAM_MESSAGE_LIMIT", "200"))
TELEGRAM_DAYS_BACK = int(os.getenv("TELEGRAM_DAYS_BACK", "30"))


def fetch_telegram_messages(chat_id: str, title: str) -> str:
    """
    Synchronous wrapper around the async Telethon client.
    Called from the ingestion pipeline which is sync.
    """
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        logger.warning(
            "TELEGRAM_API_ID / TELEGRAM_API_HASH not set — "
            "returning empty result for '%s'",
            title,
        )
        return f"[telegram not configured] Cannot fetch messages for '{title}'"

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(_run_async_fetch, chat_id, title).result()
            return result
        return loop.run_until_complete(_async_fetch_messages(chat_id, title))
    except RuntimeError:
        return asyncio.run(_async_fetch_messages(chat_id, title))


def _run_async_fetch(chat_id: str, title: str) -> str:
    return asyncio.run(_async_fetch_messages(chat_id, title))


async def _async_fetch_messages(chat_id: str, title: str) -> str:
    """Fetch messages from a Telegram channel/chat using Telethon."""
    try:
        from telethon import TelegramClient
    except ImportError:
        logger.error("telethon is not installed — pip install telethon")
        return "[error] telethon package not installed"

    session_path = os.path.join(
        os.getenv("TELEGRAM_SESSION_DIR", "/tmp"),
        TELEGRAM_SESSION,
    )

    client = TelegramClient(session_path, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)

    try:
        await client.start()

        entity = await _resolve_entity(client, chat_id)
        if entity is None:
            return f"[telegram error] Could not resolve chat: {chat_id}"

        offset_date = datetime.now(timezone.utc) - timedelta(days=TELEGRAM_DAYS_BACK)
        raw_messages: list[dict] = []

        async for msg in client.iter_messages(
            entity,
            limit=TELEGRAM_MESSAGE_LIMIT,
            offset_date=offset_date,
            reverse=True,
        ):
            if not msg.text:
                continue
            raw_messages.append({
                "id": msg.id,
                "date": msg.date.isoformat() if msg.date else "",
                "text": msg.text,
                "views": getattr(msg, "views", None),
            })

        if not raw_messages:
            return f"[telegram] No text messages found in '{title}' for the last {TELEGRAM_DAYS_BACK} days"

        blocks = _group_messages_into_blocks(raw_messages, title)
        logger.info(
            "Fetched %d messages from '%s', grouped into %d blocks",
            len(raw_messages), title, len(blocks),
        )
        return "\n\n".join(blocks)

    except Exception as exc:
        logger.exception("Telegram fetch error for '%s'", title)
        return f"[telegram error for {title}] {exc}"
    finally:
        await client.disconnect()


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
