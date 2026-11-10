"""RED/GREEN Phase 11: gateway is transparent for agent traffic and timings are per-request."""

import asyncio
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
AUTH = {"Authorization": "Bearer sk-atlas-demo-key"}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "run a query",
            "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
        },
    }
]
AGENT_BODY = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "you are a sql agent"},
        {"role": "user", "content": "count rows"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "run_sql", "arguments": '{"q":"select 1"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "1"},
    ],
    "tools": TOOLS,
    "tool_choice": "auto",
    "temperature": 0,
    "seed": 7,
}
TOOL_CALL_REPLY = {
    "id": "chatcmpl-tc",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {"name": "run_sql", "arguments": "{}"},
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ],
}


def _write(tmp_path: Path):
    t = tmp_path / "t.yaml"
    t.write_text(
        "tenants:\n  - id: demo\n    api_key: sk-atlas-demo-key\n    rpm_limit: 1000\n"
        f"    allowed_models:\n      - {MODEL}\n",
        encoding="utf-8",
    )
    w = tmp_path / "w.yaml"
    w.write_text(
        f"workers:\n  - id: worker-a\n    model: {MODEL}\n    base_url: http://fake/v1\n",
        encoding="utf-8",
    )
    return t, w


class AsyncFake:
    def __init__(self):
        self.calls: list[dict] = []

    async def chat_completions(self, payload, stats):
        self.calls.append(payload)
        stats.update(
            request_id="chatcmpl-tc", ttft_ms=None, completion_ms=1.0, status="ok", tokens_per_s=None
        )
        return TOOL_CALL_REPLY

    async def stream_chat_completions(self, payload, stats):
        self.calls.append(payload)
        yield 'data: {"id":"s","choices":[{"delta":{"tool_calls":[{"index":0}]}}]}\n\n'
        yield "data: [DONE]\n\n"
        stats.update(request_id="s", ttft_ms=1.0, completion_ms=2.0, status="ok", tokens_per_s=None)


def _app(tmp_path: Path, fake):
    from app import create_app

    t, w = _write(tmp_path)
    return create_app(tenants_path=t, workers_path=w, worker_client_factory=lambda _u: fake)


def test_non_stream_agent_request_reaches_upstream_unmodified(tmp_path: Path):
    fake = AsyncFake()
    client = TestClient(_app(tmp_path, fake))

    res = client.post("/v1/chat/completions", headers=AUTH, json=AGENT_BODY)

    assert res.status_code == 200
    assert fake.calls == [AGENT_BODY]
    assert res.json() == TOOL_CALL_REPLY


def test_stream_agent_request_reaches_upstream_unmodified(tmp_path: Path):
    fake = AsyncFake()
    client = TestClient(_app(tmp_path, fake))

    with client.stream(
        "POST", "/v1/chat/completions", headers=AUTH, json={**AGENT_BODY, "stream": True}
    ) as res:
        assert res.status_code == 200
        text = "".join(res.iter_text())

    assert fake.calls == [{**AGENT_BODY, "stream": True}]
    assert "tool_calls" in text and "[DONE]" in text


@pytest.mark.parametrize(
    "body",
    [
        {"model": MODEL, "messages": ["nope"]},
        {"model": MODEL, "messages": [{"content": "no role"}]},
        {"model": MODEL, "messages": []},
        {"model": MODEL, "messages": [{"role": "user", "content": "x"}], "stream": "yes"},
    ],
)
def test_malformed_bodies_are_rejected_before_upstream(tmp_path: Path, body):
    fake = AsyncFake()
    client = TestClient(_app(tmp_path, fake))

    res = client.post("/v1/chat/completions", headers=AUTH, json=body)

    assert res.status_code == 400
    assert fake.calls == []


def test_non_json_upstream_reply_is_a_502_not_a_crash(tmp_path: Path):
    class GarbageFake:
        async def chat_completions(self, payload, stats):
            stats.update(status="error", completion_ms=1.0)
            raise ValueError("upstream sent non-JSON")

        async def stream_chat_completions(self, payload, stats):
            raise AssertionError("not used")
            yield  # pragma: no cover

    app = _app(tmp_path, GarbageFake())
    client = TestClient(app, raise_server_exceptions=False)

    res = client.post("/v1/chat/completions", headers=AUTH, json=AGENT_BODY)

    assert res.status_code == 502
    assert res.json()["error"]["type"] == "upstream_error"
    assert app.state.loads in ({}, {"worker-a": 0})  # in-flight load released


def test_concurrent_streams_report_their_own_ttft(tmp_path: Path):
    """20 overlapping streams through one shared client: each event keeps its own TTFT."""
    n = 20

    class StaggeredFake:
        async def chat_completions(self, payload, stats):
            raise AssertionError("not used")

        async def stream_chat_completions(self, payload, stats):
            i = int(payload["messages"][0]["content"])
            yield 'data: {"id":"x","choices":[{"delta":{"content":"a"}}]}\n\n'
            await asyncio.sleep(0.2 - i * 0.005)  # later requests finish first
            yield "data: [DONE]\n\n"
            stats.update(
                request_id=f"r{i}", ttft_ms=1000.0 + i, completion_ms=2000.0 + i,
                status="ok", tokens_per_s=None,
            )

    app = _app(tmp_path, StaggeredFake())

    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            async def one(i: int):
                r = await c.post(
                    "/v1/chat/completions",
                    headers=AUTH,
                    json={"model": MODEL, "stream": True,
                          "messages": [{"role": "user", "content": str(i)}]},
                )
                assert r.status_code == 200

            await asyncio.gather(*(one(i) for i in range(n)))

    asyncio.run(run())

    events = app.state.metrics.events.snapshot(limit=100)
    assert sorted(e["ttft_ms"] for e in events) == [1000.0 + i for i in range(n)]
    assert sorted(e["completion_ms"] for e in events) == [2000.0 + i for i in range(n)]
