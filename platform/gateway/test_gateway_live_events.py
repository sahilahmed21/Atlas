"""Phase 5.5: gateway live event feed + dashboard (AC-003–006)."""

from pathlib import Path

from fastapi.testclient import TestClient

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def _tenants_yaml(path: Path) -> Path:
    path.write_text(
        "tenants:\n"
        "  - id: demo\n"
        "    api_key: sk-atlas-demo-key\n"
        "    rpm_limit: 600\n"
        "    allowed_models:\n"
        f"      - {MODEL}\n",
        encoding="utf-8",
    )
    return path


def _workers_yaml(path: Path) -> Path:
    path.write_text(
        "workers:\n"
        "  - id: worker-a\n"
        f"    model: {MODEL}\n"
        "    base_url: http://fake-worker/v1\n"
        "  - id: worker-b\n"
        f"    model: {MODEL}\n"
        "    base_url: http://fake-worker-b/v1\n",
        encoding="utf-8",
    )
    return path


class FakeWorkerClient:
    def __init__(self):
        self.last_timings = {
            "request_id": "chatcmpl-fake",
            "ttft_ms": 11.0,
            "completion_ms": 22.0,
            "status": "ok",
            "tokens_per_s": 50.0,
        }

    def chat_completions(self, payload: dict) -> dict:
        return {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "model": payload.get("model", MODEL),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
        }

    def stream_chat_completions(self, payload: dict):
        yield 'data: {"id":"x","choices":[{"delta":{"content":"ok"}}]}\n\n'
        yield "data: [DONE]\n\n"


def _client(tmp_path: Path, strategy: str = "round_robin") -> TestClient:
    from app import create_app

    app = create_app(
        tenants_path=_tenants_yaml(tmp_path / "tenants.yaml"),
        workers_path=_workers_yaml(tmp_path / "workers.yaml"),
        strategy=strategy,
        worker_client_factory=lambda _url: FakeWorkerClient(),
    )
    return TestClient(app)


def test_chat_publishes_live_event(tmp_path: Path):
    client = _client(tmp_path)
    headers = {"Authorization": "Bearer sk-atlas-demo-key"}

    res = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "secret-user-text"}],
        },
    )
    assert res.status_code == 200

    snap = client.get("/atlas/snapshot", headers=headers)
    assert snap.status_code == 200
    body = snap.json()
    assert body["events"]
    ev = body["events"][-1]
    assert ev["worker_id"] == res.headers["x-atlas-worker-id"]
    assert ev["strategy"] == res.headers["x-atlas-route-strategy"]
    assert ev["cache_signal"] == res.headers["x-atlas-cache-signal"]
    assert ev["reason"]
    assert "secret-user-text" not in str(body)


def test_atlas_snapshot_requires_auth(tmp_path: Path):
    client = _client(tmp_path)
    assert client.get("/atlas/snapshot").status_code == 401
    assert client.get("/atlas/snapshot?api_key=sk-wrong").status_code == 401
    ok = client.get("/atlas/snapshot?api_key=sk-atlas-demo-key")
    assert ok.status_code == 200


def test_atlas_events_sse_emits_after_chat(tmp_path: Path):
    """SSE catch-up replays buffered events with id > after (no concurrent POST needed)."""
    client = _client(tmp_path)
    headers = {"Authorization": "Bearer sk-atlas-demo-key"}

    chat = client.post(
        "/v1/chat/completions",
        headers=headers,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert chat.status_code == 200

    with client.stream(
        "GET",
        "/atlas/events?api_key=sk-atlas-demo-key&after=0&catchup_only=true",
    ) as sse:
        assert sse.status_code == 200
        assert "text/event-stream" in sse.headers.get("content-type", "")
        text = "".join(sse.iter_text())
        assert "data:" in text
        assert "worker_id" in text


def test_dashboard_html_served(tmp_path: Path):
    client = _client(tmp_path)
    res = client.get("/dashboard/")
    assert res.status_code == 200
    text = res.text.lower()
    assert "html" in text or "<!doctype" in text
    assert "process-local" in text or "honesty" in text or "request path" in text
