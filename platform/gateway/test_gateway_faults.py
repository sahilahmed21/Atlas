"""RED/GREEN Phase 12: seeded fault injection at the gateway (record mode), replayed from the log."""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
SEED = 1234


class CountingUp:
    def __init__(self):
        self.calls = 0

    async def chat_completions(self, payload, stats):
        self.calls += 1
        stats.update(request_id="x", ttft_ms=None, completion_ms=1.0, status="ok", tokens_per_s=None)
        return {"id": "x", "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "fine"}}]}

    async def stream_chat_completions(self, payload, stats):
        self.calls += 1
        yield 'data: {"id":"s","choices":[{"delta":{"content":"fine"}}]}\n\n'
        yield "data: [DONE]\n\n"
        stats.update(request_id="s", ttft_ms=1.0, completion_ms=2.0, status="ok", tokens_per_s=None)


@pytest.fixture
def env(tmp_path: Path):
    from app import create_app
    from recorder import Recorder

    t = tmp_path / "t.yaml"
    t.write_text(
        f"tenants:\n  - id: a\n    api_key: sk-a\n    rpm_limit: 1000\n    record_allowed: true\n    allowed_models: [{MODEL}]\n",
        encoding="utf-8",
    )
    w = tmp_path / "w.yaml"
    w.write_text(f"workers:\n  - id: w\n    model: {MODEL}\n    base_url: http://f/v1\n", encoding="utf-8")
    up = CountingUp()
    rec = Recorder(tmp_path / "runs.db")
    client = TestClient(create_app(tenants_path=t, workers_path=w,
                                   worker_client_factory=lambda _u: up, recorder=rec))
    yield client, up, rec
    rec.close()


def _post(client, run, step, mode="record", seed=SEED, rate=1.0, stream=False, text=None):
    headers = {"Authorization": "Bearer sk-a", "x-atlas-mode": mode,
               "x-atlas-run-id": run, "x-atlas-step": str(step)}
    if seed is not None:
        headers["x-atlas-fault-seed"] = str(seed)
        headers["x-atlas-fault-rate"] = str(rate)
    body = {"model": MODEL, "stream": stream,
            "messages": [{"role": "user", "content": text or f"q{step}"}]}
    return client.post("/v1/chat/completions", headers=headers, json=body)


def _fault_of(rec, run, step):
    (row,) = [s for s in asyncio.run(rec.get_run("a", run))["steps"] if s["step"] == step]
    return row["fault"]


def test_fault_headers_are_validated_and_need_record_mode(env):
    client, up, _ = env
    assert _post(client, "r", 0, mode="live").status_code == 400
    assert _post(client, "r", 0, seed="abc").status_code == 400
    assert _post(client, "r", 0, rate=1.5).status_code == 400
    assert _post(client, "r", 0, mode="replay").status_code == 404  # replay ignores faults, finds nothing
    assert up.calls == 0


def test_rate_zero_calls_the_real_upstream_and_records_no_fault(env):
    client, up, rec = env

    res = _post(client, "r", 0, rate=0.0)

    assert res.status_code == 200 and up.calls == 1 and _fault_of(rec, "r", 0) is None


def test_applied_fault_matches_the_schedule_and_replays_without_the_seed(env):
    from recording import fault_for

    client, up, rec = env
    steps = range(40)
    recorded = {s: _post(client, "r", s) for s in steps}

    assert up.calls == 0  # rate 1.0: every step faulted, none reached the worker
    for s in steps:
        assert _fault_of(rec, "r", s) == fault_for(SEED, s, 1.0)
        replay = _post(client, "r", s, mode="replay", seed=None)  # no seed needed to replay
        assert (replay.status_code, replay.content) == (recorded[s].status_code, recorded[s].content)
        assert replay.headers["x-atlas-replay"] == "1"


def test_each_fault_kind_produces_its_failure_shape(env):
    from recording import FAULT_KINDS, fault_for

    client, up, rec = env
    step_for = {}
    for s in range(200):
        step_for.setdefault(fault_for(SEED, s, 1.0), s)
    assert set(step_for) == set(FAULT_KINDS)

    for kind, status in (("rate_limit", 429), ("server_error", 503), ("timeout", 504)):
        res = _post(client, "k", step_for[kind])
        assert res.status_code == status and res.json()["error"]["type"] in {
            "rate_limit_error", "upstream_error", "upstream_timeout"}
    for kind in ("malformed_json", "truncated_stream"):
        res = _post(client, "k", step_for[kind])
        assert res.status_code == 200
        with pytest.raises(json.JSONDecodeError):
            json.loads(res.content)


def test_same_seed_same_failures_different_seed_different_failures(env):
    client, up, rec = env
    for run, seed in (("a1", 5), ("a2", 5), ("b1", 6)):
        for s in range(30):
            _post(client, run, s, seed=seed)

    schedule = lambda run: [_fault_of(rec, run, s) for s in range(30)]
    assert schedule("a1") == schedule("a2") != schedule("b1")


def test_stream_faults_are_recorded_and_replay_byte_identically(env):
    from recording import fault_for

    client, up, rec = env
    step_for = {}
    for s in range(200):
        step_for.setdefault(fault_for(SEED, s, 1.0), s)

    def read(step, mode, seed):
        headers = {"Authorization": "Bearer sk-a", "x-atlas-mode": mode,
                   "x-atlas-run-id": "st", "x-atlas-step": str(step)}
        if seed is not None:
            headers.update({"x-atlas-fault-seed": str(seed), "x-atlas-fault-rate": "1.0"})
        body = {"model": MODEL, "stream": True, "messages": [{"role": "user", "content": f"q{step}"}]}
        with client.stream("POST", "/v1/chat/completions", headers=headers, json=body) as r:
            return r.status_code, b"".join(r.iter_bytes())

    status, truncated = read(step_for["truncated_stream"], "record", SEED)
    assert status == 200 and b"[DONE]" not in truncated and b"content" in truncated
    status, malformed = read(step_for["malformed_json"], "record", SEED)
    assert status == 200 and b"[DONE]" in malformed and b"{not valid json" in malformed
    status, limited = read(step_for["rate_limit"], "record", SEED)
    assert status == 429

    for kind, original in (("truncated_stream", truncated), ("malformed_json", malformed),
                           ("rate_limit", limited)):
        assert read(step_for[kind], "replay", None)[1] == original
    assert up.calls == 0
