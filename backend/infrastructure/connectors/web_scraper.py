import re
from html.parser import HTMLParser
from urllib import error, request


class _TextExtractor(HTMLParser):
    """Extracts visible text from HTML, skipping script/style blocks."""

    _SKIP = frozenset({"script", "style", "noscript", "svg", "head"})

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._parts.append(text)

    def get_text(self) -> str:
        raw = " ".join(self._parts)
        return re.sub(r"\s+", " ", raw).strip()


def scrape_web_content(url: str, title: str, timeout: int = 15) -> str:
    """Fetch a web page and extract its visible text content."""
    if not url:
        return ""
    req = request.Request(url, headers={"User-Agent": "llm-rag-bot/1.0"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw_bytes: bytes = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            html = raw_bytes.decode(charset, errors="replace")
    except (error.URLError, error.HTTPError, OSError, ValueError) as exc:
        return f"[scrape error for {title}] {exc}"

    parser = _TextExtractor()
    parser.feed(html)
    text = parser.get_text()
    return text[:50_000] if text else f"[no text extracted from {url}]"
