"""RED/GREEN Phase 12: streaming record/replay, oversized streams, client disconnect."""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
H = {"Authorization": "Bearer sk-a", "x-atlas-run-id": "r1"}


def _body(text="hi"):
    return {"model": MODEL, "stream": True, "messages": [{"role": "user", "content": text}]}


class StreamUpstream:
    def __init__(self, delay: float = 0.0):
        self.calls = 0
        self.delay = delay

    async def chat_completions(self, payload, stats):
        raise AssertionError("not used")

    async def stream_chat_completions(self, payload, stats):
        self.calls += 1
        n = self.calls
        yield 'data: {"id":"s%d","choices":[{"delta":{"role":"assistant"}}]}\n\n' % n
        yield 'data: {"id":"s%d","choices":[{"delta":{"content":"café"}}]}\n\n' % n
        if self.delay:
            await asyncio.sleep(self.delay)
        yield 'data: {"id":"s%d","choices":[],"usage":{"prompt_tokens":4,"completion_tokens":9}}\n\n' % n
        yield "data: [DONE]\n\n"
        stats.update(request_id=f"s{n}", ttft_ms=3.5, completion_ms=9.0, status="ok", tokens_per_s=None)


class Forbidden:
    async def chat_completions(self, payload, stats):
        raise AssertionError("replay must not reach the upstream")

    async def stream_chat_completions(self, payload, stats):
        raise AssertionError("replay must not reach the upstream")
        yield  # pragma: no cover


def _make(tmp_path: Path, upstream, recorder=None, **kwargs):
    from app import create_app
    from recorder import Recorder

    t = tmp_path / "t.yaml"
    t.write_text(
        f"tenants:\n  - id: a\n    api_key: sk-a\n    rpm_limit: 1000\n    record_allowed: true\n    allowed_models: [{MODEL}]\n",
        encoding="utf-8",
    )
    w = tmp_path / "w.yaml"
    w.write_text(f"workers:\n  - id: worker-a\n    model: {MODEL}\n    base_url: http://f/v1\n", encoding="utf-8")
    rec = recorder or Recorder(tmp_path / "runs.db")
    app = create_app(tenants_path=t, workers_path=w, worker_client_factory=lambda _u: upstream,
                     recorder=rec, **kwargs)
    return app, rec


def _stream(client, mode, step=0, text="hi"):
    with client.stream("POST", "/v1/chat/completions",
                       headers={**H, "x-atlas-mode": mode, "x-atlas-step": str(step)},
                       json=_body(text)) as res:
        raw = b"".join(res.iter_bytes())
        return res.status_code, raw, res.headers


def test_stream_replay_is_byte_identical_and_never_calls_the_upstream(tmp_path: Path):
    up = StreamUpstream()
    app, rec = _make(tmp_path, up)
    try:
        status, recorded, _ = _stream(TestClient(app), "record")
        assert status == 200 and b"[DONE]" in recorded and up.calls == 1

        (tmp_path / "again").mkdir()
        app2, _ = _make(tmp_path / "again", Forbidden(), recorder=rec)
        client2 = TestClient(app2)
        for _ in range(20):
            status, again, headers = _stream(client2, "replay")
            assert status == 200 and again == recorded
            assert headers["x-atlas-replay"] == "1"
    finally:
        rec.close()


def test_stream_step_stores_ttft_usage_and_worker(tmp_path: Path):
    app, rec = _make(tmp_path, StreamUpstream())
    try:
        _stream(TestClient(app), "record")
        (step,) = asyncio.run(rec.get_run("a", "r1"))["steps"]
    finally:
        rec.close()

    assert step["is_stream"] is True
    assert (step["ttft_ms"], step["completion_ms"]) == (3.5, 9.0)
    assert (step["prompt_tokens"], step["completion_tokens"]) == (4, 9)
    assert step["worker_id"] == "worker-a" and step["outcome"] == "ok"


def test_retry_of_a_recorded_stream_is_served_from_the_store(tmp_path: Path):
    up = StreamUpstream()
    app, rec = _make(tmp_path, up)
    try:
        client = TestClient(app)
        _, first, _ = _stream(client, "record")
        _, second, headers = _stream(client, "record")
    finally:
        rec.close()

    assert up.calls == 1 and second == first and headers["x-atlas-replay"] == "1"


def test_oversized_stream_reaches_the_client_but_marks_the_run_incomplete(tmp_path: Path):
    up = StreamUpstream()
    app, rec = _make(tmp_path, up, record_max_bytes=50)
    try:
        client = TestClient(app)
        status, body, _ = _stream(client, "record")
        run = asyncio.run(rec.get_run("a", "r1"))
        replay = client.post("/v1/chat/completions",
                             headers={**H, "x-atlas-mode": "replay", "x-atlas-step": "0"}, json=_body())
    finally:
        rec.close()

    assert status == 200 and b"[DONE]" in body  # the live client is never short-changed
    assert run["status"] == "incomplete" and run["steps"] == []
    assert replay.status_code == 404 and replay.json()["error"]["run_status"] == "incomplete"


def test_client_disconnect_mid_stream_marks_the_run_incomplete(tmp_path: Path):
    up = StreamUpstream(delay=0.5)
    app, rec = _make(tmp_path, up)

    async def go():
        sent = []
        first = True

        async def receive():
            nonlocal first
            if first:
                first = False
                return {"type": "http.request", "body": json.dumps(_body()).encode(), "more_body": False}
            await asyncio.sleep(0.1)
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        headers = {**H, "x-atlas-mode": "record", "x-atlas-step": "0", "content-type": "application/json"}
        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
            "scheme": "http", "path": "/v1/chat/completions", "raw_path": b"/v1/chat/completions",
            "query_string": b"", "root_path": "", "server": ("t", 80), "client": ("c", 1),
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        }
        await app(scope, receive, send)
        await asyncio.sleep(0.2)  # let the writer thread apply the fire-and-forget flag
        return await rec.get_run("a", "r1")

    try:
        run = asyncio.run(go())
    finally:
        rec.close()

    assert run["status"] == "incomplete" and run["steps"] == []
