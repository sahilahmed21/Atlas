"""Reference SQL agent: a plain tool-calling loop over the gateway's OpenAI-compatible API.

Every request carries run/step headers so the gateway records (or replays) the run. The step
counter advances on every HTTP request, including retries after an upstream failure: a failed
step is part of the recorded history and a retry must not collide with it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from dataset import SCHEMA
from sql_tool import SqlTool

SYSTEM = (
    "You answer questions about a sales database using the run_sql tool (SQLite, read-only).\n"
    f"Schema:\n{SCHEMA}\n"
    "Run queries as needed. When you know the answer, reply with a final line: ANSWER: <value>"
)
TOOLS = [{
    "type": "function",
    "function": {
        "name": "run_sql",
        "description": "Run one read-only SQL SELECT statement and get rows back as JSON.",
        "parameters": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]},
    },
}]
MAX_CONSECUTIVE_HTTP_ERRORS = 3


@dataclass
class AgentResult:
    final_text: str | None
    status: str  # answered | max_steps | http_error | replay_error
    requests: int
    tool_calls: int
    tags: list[str] = field(default_factory=list)


async def run_agent(
    client: httpx.AsyncClient,
    *,
    model: str,
    question: str,
    tool: SqlTool,
    run_id: str,
    api_key: str,
    max_steps: int = 8,
    mode: str = "record",
    user_tag: str | None = None,
    fault_seed: int | None = None,
    fault_rate: float | None = None,
) -> AgentResult:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    tags: list[str] = []
    tool_calls = http_errors = 0
    for step in range(max_steps):
        headers = {"Authorization": f"Bearer {api_key}", "x-atlas-mode": mode,
                   "x-atlas-run-id": run_id, "x-atlas-step": str(step)}
        if fault_seed is not None and mode == "record":
            headers["x-atlas-fault-seed"] = str(fault_seed)
            headers["x-atlas-fault-rate"] = str(1.0 if fault_rate is None else fault_rate)
        res = await client.post(
            "/v1/chat/completions", headers=headers,
            json={"model": model, "messages": messages, "tools": TOOLS, "tool_choice": "auto",
                  "temperature": 0, "user": user_tag or run_id},
        )
        try:
            if res.status_code != 200:
                raise ValueError(f"http {res.status_code}")
            message = res.json()["choices"][0]["message"]
            http_errors = 0
        except (ValueError, KeyError, IndexError):
            if mode == "replay":  # a replay that cannot be served is a divergence, not a retry
                return AgentResult(None, "replay_error", step + 1, tool_calls, tags + ["replay_error"])
            tags.append("http_error" if res.status_code != 200 else "malformed_response")
            http_errors += 1
            if http_errors >= MAX_CONSECUTIVE_HTTP_ERRORS:
                return AgentResult(None, "http_error", step + 1, tool_calls, _uniq(tags + ["http_error"]))
            continue

        calls = message.get("tool_calls")
        if not calls:
            return AgentResult(message.get("content"), "answered", step + 1, tool_calls, _uniq(tags))
        messages.append(message)
        for call in calls:
            tool_calls += 1
            try:
                sql = json.loads(call["function"]["arguments"])["sql"]
                output = tool.run(sql)
            except (ValueError, KeyError, TypeError):
                tags.append("bad_tool_args")
                output = json.dumps({"error": "invalid tool arguments"})
            if '"error"' in output:
                tags.append("tool_error")
            messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": output})
    return AgentResult(None, "max_steps", max_steps, tool_calls, _uniq(tags + ["max_steps"]))


def _uniq(tags: list[str]) -> list[str]:
    return list(dict.fromkeys(tags))
