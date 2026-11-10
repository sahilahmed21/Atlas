"""Deterministic offline stand-in for an LLM, used to validate the eval pipeline itself.

It is NOT evidence about any real model: it succeeds on a task with probability q (decided by a
seeded RNG per (seed, trial, task)), optionally typos its first SQL, and answers with whatever
the tool returned. Plugged in as the gateway's worker client, so the whole record/replay/eval
path runs without a provider.
"""

from __future__ import annotations

import json
import random
from typing import Any

from tasks import TASKS

_BY_QUESTION = {t.question: t for t in TASKS}


def _tool_call(n: int, sql: str) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": f"call_{n}", "type": "function",
             "function": {"name": "run_sql", "arguments": json.dumps({"sql": sql})}}
        ],
    }


class ScriptedModel:
    def __init__(self, q: float = 1.0, seed: int = 0, typo_rate: float = 0.0,
                 never_answers: bool = False) -> None:
        self.q, self.seed, self.typo_rate, self.never_answers = q, seed, typo_rate, never_answers
        self.calls = 0

    async def chat_completions(self, payload: dict[str, Any], stats: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        messages = payload["messages"]
        task = _BY_QUESTION[messages[1]["content"]]
        rng = random.Random(f"{self.seed}:{payload.get('user', '')}:{task.id}")
        good, typo = rng.random() < self.q, rng.random() < self.typo_rate
        tool_msgs = [m for m in messages if m["role"] == "tool"]
        correct_sql = task.sql if good else "SELECT 0"

        if not tool_msgs:
            message = _tool_call(0, ("SELEC " + correct_sql) if typo else correct_sql)
        else:
            last = json.loads(tool_msgs[-1]["content"])
            if "error" in last:
                message = _tool_call(len(tool_msgs), correct_sql)
            elif self.never_answers:
                message = _tool_call(len(tool_msgs), correct_sql)
            else:
                message = {"role": "assistant", "content": f"ANSWER: {last['rows'][0][0]}"}

        prompt_tokens = len(json.dumps(messages)) // 4
        completion_tokens = len(json.dumps(message)) // 4
        stats.update(request_id="scripted", ttft_ms=None, completion_ms=1.0, status="ok", tokens_per_s=None)
        return {
            "id": f"chatcmpl-{self.calls}",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": message,
                         "finish_reason": "tool_calls" if "tool_calls" in message else "stop"}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                      "total_tokens": prompt_tokens + completion_tokens},
        }

    async def stream_chat_completions(self, payload, stats):
        raise AssertionError("the eval agent does not stream")
        yield  # pragma: no cover
