"""Thin OpenAI-compatible client for a vLLM (or fake) worker."""

from __future__ import annotations

import json
import time
from typing import Any, Iterator

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
        self.last_timings: dict[str, Any] = {
            "request_id": None,
            "ttft_ms": None,
            "completion_ms": None,
            "status": "ok",
            "tokens_per_s": None,
        }

    def chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            res = self.http.post("/chat/completions", json=payload)
            res.raise_for_status()
            body = res.json()
        except Exception:
            self.last_timings = {
                "request_id": None,
                "ttft_ms": None,
                "completion_ms": (time.perf_counter() - t0) * 1000,
                "status": "error",
                "tokens_per_s": None,
            }
            raise
        completion_ms = (time.perf_counter() - t0) * 1000
        self.last_timings = {
            "request_id": body.get("id"),
            "ttft_ms": None,  # non-stream: no first-token signal
            "completion_ms": completion_ms,
            "status": "ok",
            "tokens_per_s": _tokens_per_s(body, completion_ms),
        }
        return body

    def stream_chat_completions(self, payload: dict[str, Any]) -> Iterator[str]:
        body = dict(payload)
        body["stream"] = True
        t0 = time.perf_counter()
        ttft_ms: float | None = None
        request_id: str | None = None
        status = "ok"
        stream_cm = None
        try:
            stream_cm = self.http.stream("POST", "/chat/completions", json=body)
            res = stream_cm.__enter__()
            res.raise_for_status()
            for line in res.iter_lines():
                if not line:
                    continue
                if (
                    ttft_ms is None
                    and line.startswith("data:")
                    and "[DONE]" not in line
                ):
                    ttft_ms = (time.perf_counter() - t0) * 1000
                    raw = line[5:].strip()
                    try:
                        chunk = json.loads(raw)
                        request_id = chunk.get("id") or request_id
                    except json.JSONDecodeError:
                        pass
                yield f"{line}\n\n"
        except Exception:
            status = "error"
            self.last_timings = {
                "request_id": request_id,
                "ttft_ms": ttft_ms,
                "completion_ms": (time.perf_counter() - t0) * 1000,
                "status": status,
                "tokens_per_s": None,
            }
            raise
        finally:
            if stream_cm is not None:
                stream_cm.__exit__(None, None, None)
            if status == "ok":
                self.last_timings = {
                    "request_id": request_id,
                    "ttft_ms": ttft_ms,
                    "completion_ms": (time.perf_counter() - t0) * 1000,
                    "status": status,
                    "tokens_per_s": None,
                }

    def close(self) -> None:
        if self._owns_http:
            self.http.close()


def _tokens_per_s(body: dict[str, Any], completion_ms: float) -> float | None:
    usage = body.get("usage") or {}
    total = usage.get("completion_tokens")
    if total is None or completion_ms <= 0:
        return None
    return float(total) / (completion_ms / 1000.0)
