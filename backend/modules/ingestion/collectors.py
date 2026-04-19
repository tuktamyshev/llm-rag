import logging

from infrastructure.connectors.telegram_client import fetch_telegram_messages
from infrastructure.connectors.web_scraper import scrape_web_content
from modules.sources.models import Source, SourceType

logger = logging.getLogger(__name__)


def collect_source_text(source: Source) -> str:
    if source.source_type == SourceType.WEB:
        return collect_web_source(source.uri or "", source.title)
    if source.source_type == SourceType.TELEGRAM:
        chat_id = source.external_id or source.uri or ""
        return collect_telegram_source(chat_id, source.title)
    logger.warning("Unknown source type: %s", source.source_type)
    return ""


def collect_web_source(url: str, title: str) -> str:
    """Scrape and extract text from a web page."""
    return scrape_web_content(url, title)


def collect_telegram_source(chat_id: str, title: str) -> str:
    """Fetch recent text messages from a Telegram channel or chat."""
    return fetch_telegram_messages(chat_id, title)
