"""Async OpenAI-compatible client for a vLLM (or hosted) worker.

Timings are written to a caller-owned ``stats`` dict, never to the client, so one
shared client can serve many concurrent requests without mixing their numbers.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

import httpx


def _fill(
    stats: dict[str, Any],
    *,
    request_id: str | None,
    ttft_ms: float | None,
    completion_ms: float | None,
    status: str,
    tokens_per_s: float | None = None,
) -> None:
    stats.update(
        request_id=request_id,
        ttft_ms=ttft_ms,
        completion_ms=completion_ms,
        status=status,
        tokens_per_s=tokens_per_s,
    )


def _has_output(chunk: dict[str, Any] | None) -> bool:
    """True when a stream chunk carries content or a tool call (not a role-only chunk)."""
    for choice in (chunk or {}).get("choices") or []:
        delta = choice.get("delta") or {}
        if delta.get("content") or delta.get("tool_calls"):
            return True
    return False


class OpenAIWorkerClient:
    def __init__(
        self,
        base_url: str,
        http: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
        api_key: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_http = http is None
        self.http = http or httpx.AsyncClient(base_url=self.base_url, timeout=timeout)
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def chat_completions(
        self, payload: dict[str, Any], stats: dict[str, Any]
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            res = await self.http.post(
                "/chat/completions", json=payload, headers=self._headers
            )
            res.raise_for_status()
            body = res.json()
        except Exception:
            _fill(
                stats,
                request_id=None,
                ttft_ms=None,
                completion_ms=(time.perf_counter() - t0) * 1000,
                status="error",
            )
            raise
        completion_ms = (time.perf_counter() - t0) * 1000
        _fill(
            stats,
            request_id=body.get("id"),
            ttft_ms=None,  # non-stream: no first-token signal
            completion_ms=completion_ms,
            status="ok",
            tokens_per_s=_tokens_per_s(body, completion_ms),
        )
        return body

    async def stream_chat_completions(
        self, payload: dict[str, Any], stats: dict[str, Any]
    ) -> AsyncIterator[str]:
        body = {**payload, "stream": True}
        t0 = time.perf_counter()
        ttft_ms: float | None = None
        request_id: str | None = None
        # "aborted" survives only if the consumer stops early (GeneratorExit/cancel).
        status = "aborted"
        try:
            async with self.http.stream(
                "POST", "/chat/completions", json=body, headers=self._headers
            ) as res:
                res.raise_for_status()
                async for line in res.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data:") and "[DONE]" not in line:
                        try:
                            chunk = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            chunk = None
                        if isinstance(chunk, dict):
                            request_id = chunk.get("id") or request_id
                            if ttft_ms is None and _has_output(chunk):
                                ttft_ms = (time.perf_counter() - t0) * 1000
                    yield f"{line}\n\n"
            status = "ok"
        except Exception:
            status = "error"
            raise
        finally:
            _fill(
                stats,
                request_id=request_id,
                ttft_ms=ttft_ms,
                completion_ms=(time.perf_counter() - t0) * 1000,
                status=status,
            )

    async def close(self) -> None:
        if self._owns_http:
            await self.http.aclose()


def _tokens_per_s(body: dict[str, Any], completion_ms: float) -> float | None:
    usage = body.get("usage") or {}
    total = usage.get("completion_tokens")
    if total is None or completion_ms <= 0:
        return None
    return float(total) / (completion_ms / 1000.0)
