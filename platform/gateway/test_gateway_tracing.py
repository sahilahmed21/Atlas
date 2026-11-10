"""RED/GREEN Phase 11b: the gateway exports one finished span per request, stream or not."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
AUTH = {"Authorization": "Bearer sk-atlas-demo-key"}
BODY = {"model": MODEL, "messages": [{"role": "user", "content": "hi"}]}


class Fake:
    async def chat_completions(self, payload, stats):
        stats.update(request_id="x", ttft_ms=None, completion_ms=1.0, status="ok", tokens_per_s=None)
        return {"id": "x", "object": "chat.completion", "choices": []}

    async def stream_chat_completions(self, payload, stats):
        yield 'data: {"id":"x","choices":[{"delta":{"content":"a"}}]}\n\n'
        yield "data: [DONE]\n\n"
        stats.update(request_id="x", ttft_ms=1.0, completion_ms=2.0, status="ok", tokens_per_s=None)


@pytest.fixture
def exporter():
    import otel_hooks

    exp = InMemorySpanExporter()
    otel_hooks.configure_tracing(exp)
    yield exp
    otel_hooks.configure_tracing()  # no env configured -> tracing off again


def _client(tmp_path: Path) -> TestClient:
    from app import create_app

    t = tmp_path / "t.yaml"
    t.write_text(
        "tenants:\n  - id: demo\n    api_key: sk-atlas-demo-key\n    rpm_limit: 100\n"
        f"    allowed_models: [{MODEL}]\n",
        encoding="utf-8",
    )
    w = tmp_path / "w.yaml"
    w.write_text(
        f"workers:\n  - id: worker-a\n    model: {MODEL}\n    base_url: http://fake/v1\n",
        encoding="utf-8",
    )
    return TestClient(
        create_app(tenants_path=t, workers_path=w, worker_client_factory=lambda _u: Fake())
    )


def _chat_spans(exporter):
    return [s for s in exporter.get_finished_spans() if s.name == "atlas.chat_completions"]


def test_non_stream_request_exports_one_span_with_route_and_outcome(tmp_path: Path, exporter):
    assert _client(tmp_path).post("/v1/chat/completions", headers=AUTH, json=BODY).status_code == 200

    (span,) = _chat_spans(exporter)
    assert span.attributes["atlas.tenant_id"] == "demo"
    assert span.attributes["atlas.worker_id"] == "worker-a"
    assert span.attributes["atlas.outcome"] == "ok"


def test_stream_request_span_finishes_after_stream_ends(tmp_path: Path, exporter):
    client = _client(tmp_path)

    with client.stream(
        "POST", "/v1/chat/completions", headers=AUTH, json={**BODY, "stream": True}
    ) as res:
        "".join(res.iter_text())

    (span,) = _chat_spans(exporter)
    assert span.attributes["atlas.outcome"] == "ok"
    assert span.end_time is not None


def test_tracing_is_a_noop_when_not_configured(tmp_path: Path):
    import otel_hooks

    otel_hooks.configure_tracing()  # no exporter, no env

    assert _client(tmp_path).post("/v1/chat/completions", headers=AUTH, json=BODY).status_code == 200
