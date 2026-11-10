"""RED/GREEN Phase 12: tenant-scoped run API (inspect, end)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


class Up:
    async def chat_completions(self, payload, stats):
        stats.update(request_id="x", ttft_ms=None, completion_ms=1.0, status="ok", tokens_per_s=None)
        return {"id": "x", "object": "chat.completion", "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "SECRET-ANSWER"}}]}

    async def stream_chat_completions(self, payload, stats):
        raise AssertionError("unused")
        yield  # pragma: no cover


@pytest.fixture
def env(tmp_path: Path):
    from app import create_app
    from recorder import Recorder

    t = tmp_path / "t.yaml"
    t.write_text(
        "tenants:\n"
        f"  - id: a\n    api_key: sk-a\n    rpm_limit: 100\n    record_allowed: true\n    allowed_models: [{MODEL}]\n"
        f"  - id: b\n    api_key: sk-b\n    rpm_limit: 100\n    record_allowed: true\n    allowed_models: [{MODEL}]\n"
        f"  - id: c\n    api_key: sk-c\n    rpm_limit: 100\n    allowed_models: [{MODEL}]\n",
        encoding="utf-8",
    )
    w = tmp_path / "w.yaml"
    w.write_text(f"workers:\n  - id: w\n    model: {MODEL}\n    base_url: http://f/v1\n", encoding="utf-8")
    rec = Recorder(tmp_path / "runs.db")
    client = TestClient(create_app(tenants_path=t, workers_path=w,
                                   worker_client_factory=lambda _u: Up(), recorder=rec))
    yield client
    rec.close()


def _record(client, run, step, text="hi", key="sk-a"):
    return client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "x-atlas-mode": "record",
                 "x-atlas-run-id": run, "x-atlas-step": str(step)},
        json={"model": MODEL, "messages": [{"role": "user", "content": text}]},
    )


def _auth(key="sk-a"):
    return {"Authorization": f"Bearer {key}"}


def test_get_run_lists_step_summaries_without_content(env):
    _record(env, "run/1", 0)
    _record(env, "run/1", 1, "again")

    res = env.get("/atlas/runs/run/1", headers=_auth())

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "open" and [s["step"] for s in body["steps"]] == [0, 1]
    assert "SECRET-ANSWER" not in res.text


def test_runs_are_invisible_to_other_tenants_and_unauthorised_callers(env):
    _record(env, "r1", 0)

    assert env.get("/atlas/runs/r1", headers=_auth("sk-b")).status_code == 404
    assert env.post("/atlas/runs/r1/end", headers=_auth("sk-b")).status_code == 404
    assert env.get("/atlas/runs/r1").status_code == 401
    assert env.get("/atlas/runs/r1", headers=_auth("sk-c")).status_code == 403  # may not record


def test_ending_a_run_closes_it_and_rejects_new_steps(env):
    _record(env, "r1", 0)

    ended = env.post("/atlas/runs/r1/end", headers=_auth())

    assert ended.status_code == 200 and ended.json() == {"run_id": "r1", "status": "closed"}
    late = _record(env, "r1", 1, "late")
    assert late.status_code == 409 and late.json()["error"]["type"] == "run_closed"
    assert env.get("/atlas/runs/r1", headers=_auth()).json()["status"] == "closed"
    assert _record(env, "r1", 0).status_code == 200  # an already-recorded step is still retry-safe


def test_ending_an_unknown_run_is_a_404(env):
    assert env.post("/atlas/runs/nope/end", headers=_auth()).status_code == 404
