"""Thin OpenAI-compatible client for a vLLM (or fake) worker."""

from __future__ import annotations

from typing import Any

import httpx


class OpenAIWorkerClient:
    def __init__(
        self,
        base_url: str,
        http: httpx.Client | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_http = http is None
        self.http = http or httpx.Client(base_url=self.base_url, timeout=timeout)

    def chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        res = self.http.post("/chat/completions", json=payload)
        res.raise_for_status()
        return res.json()

    def close(self) -> None:
        if self._owns_http:
            self.http.close()
