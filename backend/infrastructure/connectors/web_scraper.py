from __future__ import annotations

import logging
from urllib import error, request

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 100_000

# Browser-like defaults — many sites return 403 for obvious bot User-Agents.
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru,en-US;q=0.9,en;q=0.8",
}


class ScrapeError(Exception):
    """Page fetch failed or no article text could be extracted (do not index as content)."""


def scrape_web_content(url: str, title: str, timeout: int = 15) -> str:
    """Fetch a web page and extract its visible text content using trafilatura + bs4 fallback."""
    if not url:
        raise ScrapeError("Пустой URL источника")

    req = request.Request(url, headers=_DEFAULT_HEADERS)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw_bytes: bytes = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            html = raw_bytes.decode(charset, errors="replace")
    except (error.URLError, error.HTTPError, OSError, ValueError) as exc:
        logger.warning("Scrape error for %s (%s): %s", title, url, exc)
        raise ScrapeError(str(exc)) from exc

    text = _extract_with_trafilatura(html)
    if not text:
        text = _extract_with_bs4(html)
    if not text:
        logger.warning("No extractable text for %s (%s)", title, url)
        raise ScrapeError(f"Не удалось извлечь текст со страницы: {url}")

    return text[:MAX_CONTENT_LENGTH]


def _extract_with_trafilatura(html: str) -> str:
    """Primary extraction using trafilatura — optimized for article / main content."""
    try:
        import trafilatura

        result = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=False,
        )
        return result or ""
    except Exception:
        logger.debug("trafilatura extraction failed, falling back to bs4")
        return ""


def _extract_with_bs4(html: str) -> str:
    """Fallback extraction using BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "head", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())
    except Exception:
        logger.debug("bs4 extraction failed")
        return ""
