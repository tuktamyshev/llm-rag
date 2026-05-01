import logging

from infrastructure.connectors.telegram_client import fetch_telegram_messages
from infrastructure.connectors.web_scraper import scrape_web_content
from modules.ingestion.file_text_extract import extract_text_from_local_file
from modules.sources.file_storage import resolve_stored_file
from modules.sources.models import Source, SourceType

logger = logging.getLogger(__name__)


def collect_source_text(source: Source) -> str:
    if source.source_type == SourceType.WEB:
        return collect_web_source(source.uri or "", source.title)
    if source.source_type == SourceType.TELEGRAM:
        chat_id = source.external_id or source.uri or ""
        return collect_telegram_source(chat_id, source.title)
    if source.source_type == SourceType.FILE:
        return collect_file_source(source)
    logger.warning("Unknown source type: %s", source.source_type)
    return ""


def collect_web_source(url: str, title: str) -> str:
    """Scrape and extract text from a web page."""
    return scrape_web_content(url, title)


def collect_telegram_source(chat_id: str, title: str) -> str:
    """Fetch recent text messages from a Telegram channel or chat."""
    return fetch_telegram_messages(chat_id, title)


def collect_file_source(source: Source) -> str:
    """Read text from an uploaded file source."""
    settings = source.settings or {}
    relpath = settings.get("file_relpath")
    if not relpath or not isinstance(relpath, str):
        logger.warning("FILE source %s has no file_relpath in settings", source.id)
        return ""
    try:
        path = resolve_stored_file(relpath)
    except ValueError:
        logger.warning("Invalid file path for source %s", source.id)
        return ""
    if not path.is_file():
        logger.warning("Missing file for source %s: %s", source.id, path)
        return ""

    original_name = settings.get("original_filename")
    if not isinstance(original_name, str):
        original_name = path.name

    text = extract_text_from_local_file(path, original_name)
    if not text.strip():
        logger.warning("No text extracted from file source %s (%s)", source.id, original_name)
    return text
