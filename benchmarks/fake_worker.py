"""Simulated OpenAI worker with hit/miss + saturation latency (Phase 5 offline)."""

from __future__ import annotations

from typing import Any

from strategies import shared_prefix_key

# ponytail: toy latency model; replace with live vLLM when Colab validation runs
BASE_HIT_MS = 10.0
BASE_MISS_MS = 100.0
QUEUE_PENALTY_MS = 25.0


class SimulatedWorkerClient:
    """Labeled fake worker — never hits a GPU."""

    def __init__(
        self,
        worker_id: str,
        *,
        loads: dict[str, int] | None = None,
        base_hit_ms: float = BASE_HIT_MS,
        base_miss_ms: float = BASE_MISS_MS,
        queue_penalty_ms: float = QUEUE_PENALTY_MS,
    ) -> None:
        self.worker_id = worker_id
        self.loads = loads if loads is not None else {}
        self.base_hit_ms = base_hit_ms
        self.base_miss_ms = base_miss_ms
        self.queue_penalty_ms = queue_penalty_ms
        self._warm: set[str] = set()
        self._served = 0
        self.last_timings: dict[str, Any] = {
            "request_id": f"chatcmpl-{worker_id}",
            "ttft_ms": None,
            "completion_ms": None,
            "status": "ok",
            "tokens_per_s": None,
        }

    def _ttft_ms(self, messages: list[dict[str, Any]]) -> tuple[float, str]:
        key = shared_prefix_key(messages)
        hit = key in self._warm
        base = self.base_hit_ms if hit else self.base_miss_ms
        # Sequential matrix cannot pile real in-flight load; served_count models soft saturation
        pressure = self._served + self.loads.get(self.worker_id, 0)
        ttft = base + self.queue_penalty_ms * pressure
        return ttft, key

    def chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        messages = payload.get("messages") or []
        ttft, key = self._ttft_ms(messages)
        completion = ttft + 5.0
        self.last_timings = {
            "request_id": f"chatcmpl-{self.worker_id}-{self._served}",
            "ttft_ms": ttft,
            "completion_ms": completion,
            "status": "ok",
            "tokens_per_s": 1000.0 / completion if completion else None,
        }
        self._warm.add(key)
        self._served += 1
        return {
            "id": self.last_timings["request_id"],
            "object": "chat.completion",
            "model": payload.get("model", "simulated"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
        }

    def stream_chat_completions(self, payload: dict[str, Any]):
        result = self.chat_completions(payload)
        yield (
            f'data: {{"id":"{result["id"]}","object":"chat.completion.chunk",'
            f'"choices":[{{"index":0,"delta":{{"content":"ok"}},'
            f'"finish_reason":"stop"}}]}}\n\n'
        )
        yield "data: [DONE]\n\n"
