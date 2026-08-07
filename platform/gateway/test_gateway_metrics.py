"""RED/GREEN: gateway /metrics from request path (AC-011) + stream passthrough (AC-010)."""

from pathlib import Path

from fastapi.testclient import TestClient


MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def _tenants(path: Path) -> Path:
    path.write_text(
        "tenants:\n"
        "  - id: demo\n"
        "    api_key: sk-atlas-demo-key\n"
        "    rpm_limit: 100\n"
        "    allowed_models:\n"
        f"      - {MODEL}\n",
        encoding="utf-8",
    )
    return path


def _workers(path: Path) -> Path:
    path.write_text(
        "workers:\n"
        "  - id: worker-a\n"
        f"    model: {MODEL}\n"
        "    base_url: http://fake/v1\n",
        encoding="utf-8",
    )
    return path


class StreamFakeWorker:
    def __init__(self):
        self.calls = []
        self.last_timings = {
            "request_id": "chatcmpl-up",
            "ttft_ms": 5.0,
            "completion_ms": 15.0,
            "status": "ok",
            "tokens_per_s": None,
        }

    def chat_completions(self, payload):
        self.calls.append(("json", payload))
        return {
            "id": "chatcmpl-up",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hello"},
                    "finish_reason": "stop",
                }
            ],
        }

    def stream_chat_completions(self, payload):
        self.calls.append(("stream", payload))
        yield 'data: {"id":"chatcmpl-up","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"hel"}}]}\n\n'
        yield 'data: {"id":"chatcmpl-up","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"lo"},"finish_reason":"stop"}]}\n\n'
        yield "data: [DONE]\n\n"


def test_metrics_endpoint_after_request(tmp_path: Path):
    from app import create_app
    from atlas_metrics import AtlasMetrics
    from prometheus_client import CollectorRegistry

    reg = CollectorRegistry()
    metrics = AtlasMetrics(registry=reg)
    fake = StreamFakeWorker()
    app = create_app(
        tenants_path=_tenants(tmp_path / "t.yaml"),
        workers_path=_workers(tmp_path / "w.yaml"),
        worker_client_factory=lambda _url: fake,
        metrics=metrics,
    )
    client = TestClient(app)
    res = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-atlas-demo-key"},
        json={"model": MODEL, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert res.status_code == 200

    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    body = metrics_res.text
    assert "atlas_requests_total" in body
    assert 'tenant="demo"' in body
    assert 'worker_id="worker-a"' in body
    assert 'outcome="ok"' in body


def test_stream_uses_upstream_sse_not_json_rewrap(tmp_path: Path):
    from app import create_app

    fake = StreamFakeWorker()
    app = create_app(
        tenants_path=_tenants(tmp_path / "t.yaml"),
        workers_path=_workers(tmp_path / "w.yaml"),
        worker_client_factory=lambda _url: fake,
    )
    client = TestClient(app)

    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-atlas-demo-key"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    ) as res:
        assert res.status_code == 200
        text = "".join(res.iter_text())

    assert ("stream",) == (fake.calls[0][0],)
    assert fake.calls[0][1].get("stream") is True
    assert "hel" in text
    assert "[DONE]" in text
    # must not be the old single-chunk rewrap-only path without upstream stream call
    assert not any(c[0] == "json" for c in fake.calls)
