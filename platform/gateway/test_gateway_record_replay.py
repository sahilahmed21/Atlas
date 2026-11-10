"""RED/GREEN Phase 12: record/replay at the gateway (non-stream)."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def _h(key="sk-a", mode=None, run=None, step=None):
    h = {"Authorization": f"Bearer {key}"}
    if mode:
        h["x-atlas-mode"] = mode
    if run is not None:
        h["x-atlas-run-id"] = run
    if step is not None:
        h["x-atlas-step"] = str(step)
    return h


def _body(text="hi", **extra):
    return {"model": MODEL, "messages": [{"role": "user", "content": text}], **extra}


class EchoUpstream:
    """Reply depends on the request so cross-run contamination is detectable."""

    def __init__(self):
        self.calls = 0

    async def chat_completions(self, payload, stats):
        self.calls += 1
        text = payload["messages"][-1]["content"]
        stats.update(request_id="x", ttft_ms=None, completion_ms=1.0, status="ok", tokens_per_s=None)
        return {
            "id": f"chatcmpl-{self.calls}",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": f"echo:{text} é"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
        }

    async def stream_chat_completions(self, payload, stats):
        raise AssertionError("not used")
        yield  # pragma: no cover


class ForbiddenUpstream:
    async def chat_completions(self, payload, stats):
        raise AssertionError("replay must never reach the upstream")

    async def stream_chat_completions(self, payload, stats):
        raise AssertionError("replay must never reach the upstream")
        yield  # pragma: no cover


def _make(tmp_path: Path, upstream=None, recorder=None):
    from app import create_app
    from recorder import Recorder

    t = tmp_path / "t.yaml"
    t.write_text(
        "tenants:\n"
        f"  - id: a\n    api_key: sk-a\n    rpm_limit: 1000\n    record_allowed: true\n    allowed_models: [{MODEL}]\n"
        f"  - id: b\n    api_key: sk-b\n    rpm_limit: 1000\n    record_allowed: true\n    allowed_models: [{MODEL}]\n"
        f"  - id: c\n    api_key: sk-c\n    rpm_limit: 1000\n    allowed_models: [{MODEL}]\n",
        encoding="utf-8",
    )
    w = tmp_path / "w.yaml"
    w.write_text(
        f"workers:\n  - id: worker-a\n    model: {MODEL}\n    base_url: http://fake/v1\n",
        encoding="utf-8",
    )
    up = upstream or EchoUpstream()
    rec = recorder or Recorder(tmp_path / "runs.db")
    app = create_app(tenants_path=t, workers_path=w, worker_client_factory=lambda _u: up, recorder=rec)
    return app, up, rec


@pytest.fixture
def env(tmp_path):
    app, up, rec = _make(tmp_path)
    yield TestClient(app), up, rec, tmp_path
    rec.close()


def test_replay_returns_the_recorded_response_byte_for_byte_without_the_upstream(env):
    client, up, rec, tmp_path = env
    first = client.post("/v1/chat/completions", headers=_h(mode="record", run="r1", step=0), json=_body())
    assert first.status_code == 200 and up.calls == 1

    # A fresh gateway on the same recorder file whose upstream explodes if it is ever called.
    (tmp_path / "again").mkdir()
    app2, _, _ = _make(tmp_path / "again", upstream=ForbiddenUpstream(), recorder=rec)
    replay_client = TestClient(app2)
    for _ in range(100):
        again = replay_client.post(
            "/v1/chat/completions", headers=_h(mode="replay", run="r1", step=0), json=_body()
        )
        assert again.status_code == 200
        assert again.content == first.content
        assert again.headers["x-atlas-replay"] == "1"


def test_record_retry_with_same_request_is_served_from_the_store(env):
    client, up, rec, _ = env
    h = _h(mode="record", run="r1", step=0)
    a = client.post("/v1/chat/completions", headers=h, json=_body())
    b = client.post("/v1/chat/completions", headers=h, json=_body())

    assert up.calls == 1  # no second paid upstream call
    assert b.content == a.content
    assert b.headers["x-atlas-replay"] == "1" and "x-atlas-replay" not in a.headers


def test_same_step_with_a_different_request_is_a_409_conflict(env):
    client, up, rec, _ = env
    h = _h(mode="record", run="r1", step=0)
    client.post("/v1/chat/completions", headers=h, json=_body("one"))

    res = client.post("/v1/chat/completions", headers=h, json=_body("two"))

    assert res.status_code == 409
    assert res.json()["error"]["type"] == "run_step_conflict"
    assert up.calls == 1


def test_replay_missing_step_is_404_and_changed_request_is_a_divergence(env):
    client, up, rec, _ = env
    client.post("/v1/chat/completions", headers=_h(mode="record", run="r1", step=0), json=_body("one"))

    missing = client.post("/v1/chat/completions", headers=_h(mode="replay", run="r1", step=1), json=_body("one"))
    diverged = client.post("/v1/chat/completions", headers=_h(mode="replay", run="r1", step=0), json=_body("CHANGED"))
    no_run = client.post("/v1/chat/completions", headers=_h(mode="replay", run="nope", step=0), json=_body("one"))

    assert missing.status_code == 404 and no_run.status_code == 404
    assert diverged.status_code == 409
    err = diverged.json()["error"]
    assert err["type"] == "replay_divergence"
    assert err["step"] == 0 and err["expected_hash"] != err["actual_hash"]
    assert up.calls == 1


def test_record_mode_requires_permission_run_id_and_step(env):
    client, up, rec, _ = env
    post = lambda headers: client.post("/v1/chat/completions", headers=headers, json=_body())

    assert post(_h(key="sk-c", mode="record", run="r", step=0)).status_code == 403
    assert post(_h(mode="record", step=0)).status_code == 400
    assert post(_h(mode="record", run="r")).status_code == 400
    assert post(_h(mode="record", run="r", step="-1")).status_code == 400
    assert post(_h(mode="record", run="bad run id!", step=0)).status_code == 400
    assert post(_h(mode="bogus", run="r", step=0)).status_code == 400
    assert up.calls == 0


def test_recording_is_rejected_when_the_gateway_has_no_recorder(tmp_path: Path):
    from app import create_app

    t = tmp_path / "t.yaml"
    t.write_text(
        f"tenants:\n  - id: a\n    api_key: sk-a\n    rpm_limit: 10\n    record_allowed: true\n    allowed_models: [{MODEL}]\n",
        encoding="utf-8",
    )
    w = tmp_path / "w.yaml"
    w.write_text(f"workers:\n  - id: w\n    model: {MODEL}\n    base_url: http://f/v1\n", encoding="utf-8")
    client = TestClient(create_app(tenants_path=t, workers_path=w, worker_client_factory=lambda _u: EchoUpstream()))

    res = client.post("/v1/chat/completions", headers=_h(mode="record", run="r", step=0), json=_body())

    assert res.status_code == 400 and res.json()["error"]["type"] == "recording_disabled"


def test_one_tenant_cannot_replay_another_tenants_run(env):
    client, up, rec, _ = env
    client.post("/v1/chat/completions", headers=_h(mode="record", run="r1", step=0), json=_body())

    res = client.post("/v1/chat/completions", headers=_h(key="sk-b", mode="replay", run="r1", step=0), json=_body())

    assert res.status_code == 404


def test_upstream_failure_is_recorded_and_replays_identically(tmp_path: Path):
    class Boom:
        async def chat_completions(self, payload, stats):
            req = httpx.Request("POST", "http://f/v1/chat/completions")
            stats.update(status="error", completion_ms=1.0)
            raise httpx.HTTPStatusError("x", request=req, response=httpx.Response(503, request=req))

        async def stream_chat_completions(self, payload, stats):
            raise AssertionError("unused")
            yield  # pragma: no cover

    app, _, rec = _make(tmp_path, upstream=Boom())
    client = TestClient(app, raise_server_exceptions=False)
    try:
        failed = client.post("/v1/chat/completions", headers=_h(mode="record", run="r", step=0), json=_body())
        replayed = client.post("/v1/chat/completions", headers=_h(mode="replay", run="r", step=0), json=_body())
    finally:
        rec.close()

    assert failed.status_code == 502
    assert (replayed.status_code, replayed.content) == (502, failed.content)


def test_recorder_failure_is_a_503_not_a_silent_loss(tmp_path: Path):
    from recorder import Recorder

    class BrokenRecorder(Recorder):
        async def commit_step(self, step):
            raise OSError("disk full")

    app, up, rec = _make(tmp_path, recorder=BrokenRecorder(tmp_path / "x.db"))
    client = TestClient(app, raise_server_exceptions=False)
    try:
        res = client.post("/v1/chat/completions", headers=_h(mode="record", run="r", step=0), json=_body())
    finally:
        rec.close()

    assert res.status_code == 503
    assert res.json()["error"]["type"] == "recorder_unavailable"


def test_fifty_concurrent_runs_do_not_contaminate_each_other(tmp_path: Path):
    app, up, rec = _make(tmp_path)

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            async def one_run(i: int):
                recorded = []
                for s in range(3):
                    r = await c.post("/v1/chat/completions",
                                     headers=_h(mode="record", run=f"run-{i}", step=s),
                                     json=_body(f"run{i}-step{s}"))
                    assert r.status_code == 200
                    recorded.append(r.content)
                for s in range(3):
                    r = await c.post("/v1/chat/completions",
                                     headers=_h(mode="replay", run=f"run-{i}", step=s),
                                     json=_body(f"run{i}-step{s}"))
                    assert r.status_code == 200
                    assert r.content == recorded[s]
                    assert f"run{i}-step{s}".encode() in r.content  # its own run's data
            await asyncio.gather(*(one_run(i) for i in range(50)))

    try:
        asyncio.run(go())
    finally:
        rec.close()
    assert up.calls == 150


def test_recorded_usage_and_timings_are_stored(env):
    client, up, rec, _ = env
    client.post("/v1/chat/completions", headers=_h(mode="record", run="r1", step=0), json=_body())

    run = asyncio.run(rec.get_run("a", "r1"))

    (step,) = run["steps"]
    assert (step["prompt_tokens"], step["completion_tokens"]) == (5, 7)
    assert step["worker_id"] == "worker-a" and step["outcome"] == "ok" and step["completion_ms"] == 1.0
