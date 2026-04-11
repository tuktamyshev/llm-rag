import json
import os
from abc import ABC, abstractmethod
from urllib import error, request


class LLMClient(ABC):
    @abstractmethod
    def generate(self, *, prompt: str, system_prompt: str | None = None) -> str:
        raise NotImplementedError


class OpenRouterLLMClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_sec: int = 30,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        configured_base = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.base_url = self._build_openrouter_url(configured_base)
        self.referer = os.getenv("OPENROUTER_REFERER", "http://localhost:3000")
        self.app_title = os.getenv("OPENROUTER_APP_TITLE", "llm-rag")
        self.timeout_sec = timeout_sec

    def generate(self, *, prompt: str, system_prompt: str | None = None) -> str:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self.model, "messages": messages}
        req = request.Request(
            url=self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "HTTP-Referer": self.referer,
                "X-Title": self.app_title,
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_sec) as resp:
                body = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenRouter HTTP error: {exc.code} {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"OpenRouter connection error: {exc.reason}") from exc

        data = json.loads(body)
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter returned empty choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise RuntimeError("OpenRouter returned empty content")
        return str(content)

    @staticmethod
    def _build_openrouter_url(base: str) -> str:
        normalized = base.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"
