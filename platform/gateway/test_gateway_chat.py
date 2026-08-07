"""RED/GREEN: FastAPI OpenAI gateway + fake worker (AC-001–AC-003)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def _tenants_yaml(path: Path) -> Path:
    path.write_text(
        "tenants:\n"
        "  - id: demo\n"
        "    api_key: sk-atlas-demo-key\n"
        "    rpm_limit: 60\n"
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
    """Explicitly labeled fake — never hits a GPU."""

    def __init__(self):
        self.calls: list[dict] = []
        self.last_timings = {
            "request_id": "chatcmpl-fake",
            "ttft_ms": None,
            "completion_ms": 1.0,
            "status": "ok",
            "tokens_per_s": None,
        }

    def chat_completions(self, payload: dict) -> dict:
        self.calls.append(payload)
        return {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "model": payload.get("model", MODEL),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hello from fake"},
                    "finish_reason": "stop",
                }
            ],
        }

    def stream_chat_completions(self, payload: dict):
        self.calls.append(payload)
        self.last_timings = {
            "request_id": "chatcmpl-fake",
            "ttft_ms": 1.0,
            "completion_ms": 2.0,
            "status": "ok",
            "tokens_per_s": None,
        }
        yield (
            'data: {"id":"chatcmpl-fake","object":"chat.completion.chunk",'
            '"choices":[{"index":0,"delta":{"content":"hello from fake"},'
            '"finish_reason":"stop"}]}\n\n'
        )
        yield "data: [DONE]\n\n"


def _client(tmp_path: Path, fake: FakeWorkerClient | None = None, strategy: str = "round_robin"):
    from app import create_app

    fake = fake or FakeWorkerClient()

    def factory(base_url: str):
        return fake

    app = create_app(
        tenants_path=_tenants_yaml(tmp_path / "tenants.yaml"),
        workers_path=_workers_yaml(tmp_path / "workers.yaml"),
        strategy=strategy,
        worker_client_factory=factory,
    )
    return TestClient(app), fake


def test_chat_completions_ok_with_route_decision(tmp_path: Path):
    client, fake = _client(tmp_path)

    res = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-atlas-demo-key"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == "hello from fake"
    assert res.headers.get("x-atlas-worker-id") in {"worker-a", "worker-b"}
    assert res.headers.get("x-atlas-route-strategy") == "round_robin"
    assert res.headers.get("x-atlas-route-reason")
    assert len(fake.calls) == 1
    assert fake.calls[0]["messages"][0]["content"] == "hi"


def test_chat_completions_rejects_missing_messages(tmp_path: Path):
    client, fake = _client(tmp_path)

    res = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-atlas-demo-key"},
        json={"model": MODEL},
    )

    assert res.status_code == 400
    err = res.json()["error"]
    assert "message" in err
    assert err.get("type")
    assert fake.calls == []


def test_chat_completions_rejects_missing_model(tmp_path: Path):
    client, fake = _client(tmp_path)

    res = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-atlas-demo-key"},
        json={"messages": [{"role": "user", "content": "hi"}]},
    )

    assert res.status_code == 400
    assert fake.calls == []


def test_chat_completions_unauthorized(tmp_path: Path):
    client, fake = _client(tmp_path)

    res = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-wrong"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert res.status_code == 401
    body = res.json()
    assert "sk-wrong" not in str(body)
    assert "sk-atlas-demo-key" not in str(body)
    assert fake.calls == []


def test_chat_completions_rejects_disallowed_model(tmp_path: Path):
    client, fake = _client(tmp_path)

    res = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-atlas-demo-key"},
        json={
            "model": "not-allowed/model",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )

    assert res.status_code == 403
    assert fake.calls == []


def test_streaming_returns_sse_chunks(tmp_path: Path):
    client, fake = _client(tmp_path)

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

    assert "data:" in text
    assert "[DONE]" in text
    assert len(fake.calls) == 1
