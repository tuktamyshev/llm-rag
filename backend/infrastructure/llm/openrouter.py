from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Generator

import httpx

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    def generate(self, *, prompt: str, system_prompt: str | None = None) -> str:
        raise NotImplementedError

    def generate_stream(self, *, prompt: str, system_prompt: str | None = None) -> Generator[str, None, None]:
        """Optional streaming interface. Default falls back to non-streaming."""
        yield self.generate(prompt=prompt, system_prompt=system_prompt)


class OpenRouterLLMClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_sec: int = 60,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        configured_base = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.base_url = self._build_openrouter_url(configured_base)
        self.referer = os.getenv("OPENROUTER_REFERER", "http://localhost:3000")
        self.app_title = os.getenv("OPENROUTER_APP_TITLE", "llm-rag")
        self.timeout_sec = timeout_sec
        self._client = httpx.Client(timeout=timeout_sec)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "HTTP-Referer": self.referer,
            "X-Title": self.app_title,
        }

    def generate(self, *, prompt: str, system_prompt: str | None = None) -> str:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self.model, "messages": messages}

        try:
            resp = self._client.post(self.base_url, json=payload, headers=self._headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise RuntimeError(f"OpenRouter HTTP error: {exc.response.status_code} {detail}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"OpenRouter connection error: {exc}") from exc

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter returned empty choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise RuntimeError("OpenRouter returned empty content")
        return str(content)

    def generate_stream(self, *, prompt: str, system_prompt: str | None = None) -> Generator[str, None, None]:
        """Stream response tokens via SSE."""
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self.model, "messages": messages, "stream": True}

        try:
            with self._client.stream("POST", self.base_url, json=payload, headers=self._headers) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    import json
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    token = delta.get("content")
                    if token:
                        yield token
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"OpenRouter stream error: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"OpenRouter connection error: {exc}") from exc

    @staticmethod
    def _build_openrouter_url(base: str) -> str:
        normalized = base.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"
