from infrastructure.connectors.telegram_client import fetch_telegram_messages
from infrastructure.connectors.web_scraper import scrape_web_content
from modules.sources.models import Source, SourceType


def collect_source_text(source: Source) -> str:
    if source.source_type == SourceType.WEB:
        return collect_web_source(source.uri or "", source.title)
    if source.source_type == SourceType.TELEGRAM:
        return collect_telegram_source(source.external_id or "", source.title)
    return ""


def collect_web_source(url: str, title: str) -> str:
    """
    Web scraping stub (placeholder for Scrapy integration).
    """
    return scrape_web_content(url, title)


def collect_telegram_source(chat_id: str, title: str) -> str:
    """
    Telegram fetching stub (placeholder for Telethon integration).
    """
    return fetch_telegram_messages(chat_id, title)
