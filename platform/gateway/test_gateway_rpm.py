"""RED/GREEN: gateway enforces process-local RPM (AC-008)."""

from pathlib import Path

from fastapi.testclient import TestClient


MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def _tenants(path: Path, rpm: int = 2) -> Path:
    path.write_text(
        "tenants:\n"
        "  - id: demo\n"
        "    api_key: sk-atlas-demo-key\n"
        f"    rpm_limit: {rpm}\n"
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


class FakeWorker:
    def __init__(self):
        self.calls = []

    def chat_completions(self, payload):
        self.calls.append(payload)
        return {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
        }

    def stream_chat_completions(self, payload):
        raise AssertionError("non-stream test")


def test_third_request_returns_429_with_rpm_scope(tmp_path: Path):
    from app import create_app

    fake = FakeWorker()
    app = create_app(
        tenants_path=_tenants(tmp_path / "t.yaml", rpm=2),
        workers_path=_workers(tmp_path / "w.yaml"),
        worker_client_factory=lambda _url: fake,
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer sk-atlas-demo-key"}
    body = {"model": MODEL, "messages": [{"role": "user", "content": "hi"}]}

    r1 = client.post("/v1/chat/completions", headers=headers, json=body)
    r2 = client.post("/v1/chat/completions", headers=headers, json=body)
    r3 = client.post("/v1/chat/completions", headers=headers, json=body)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.headers.get("x-atlas-rpm-scope") == "process-local"
    assert r1.headers.get("x-atlas-rpm-scope") == "process-local"
    assert len(fake.calls) == 2
