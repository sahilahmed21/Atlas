"""Phase 5: gateway maintains prefix_owners + in-flight loads (AC-003–005)."""

from pathlib import Path

from fastapi.testclient import TestClient

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
SYSTEM = "You are a helpful Atlas assistant."


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
                    "message": {"role": "assistant", "content": "ok"},
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
            '"choices":[{"index":0,"delta":{"content":"ok"},'
            '"finish_reason":"stop"}]}\n\n'
        )
        yield "data: [DONE]\n\n"


def _app(
    tmp_path: Path,
    strategy: str,
    fake: FakeWorkerClient | None = None,
    *,
    load_margin: int = 0,
):
    from app import create_app

    fake = fake or FakeWorkerClient()
    app = create_app(
        tenants_path=_tenants_yaml(tmp_path / "tenants.yaml"),
        workers_path=_workers_yaml(tmp_path / "workers.yaml"),
        strategy=strategy,
        worker_client_factory=lambda _url: fake,
        load_margin=load_margin,
    )
    return app, fake


def _chat(client: TestClient, user: str, *, stream: bool = False):
    return client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-atlas-demo-key"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
            ],
            "stream": stream,
        },
    )


def test_prefix_aware_owner_writeback_and_hit(tmp_path: Path):
    app, _fake = _app(tmp_path, "prefix_aware")
    client = TestClient(app)

    r1 = _chat(client, "question about cats")
    r2 = _chat(client, "question about dogs")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.headers["x-atlas-cache-signal"] == "miss"
    assert r2.headers["x-atlas-cache-signal"] == "hit"
    assert r1.headers["x-atlas-worker-id"] == r2.headers["x-atlas-worker-id"]
    assert app.state.prefix_owners, "owner map must be claimed after miss"


def test_prefix_aware_load_gate_breaks_sticky_under_served_pressure(tmp_path: Path):
    """AC-004: with load_margin>0, soft served pressure breaks sticky to cooler worker."""
    app, _fake = _app(tmp_path, "prefix_aware", load_margin=1)
    client = TestClient(app)

    r1 = _chat(client, "q1")
    assert r1.status_code == 200
    assert r1.headers["x-atlas-cache-signal"] == "miss"
    owner = r1.headers["x-atlas-worker-id"]

    r2 = _chat(client, "q2")
    assert r2.status_code == 200
    # served[owner]=1, alt=0, margin=1 → break on second request
    assert r2.headers["x-atlas-cache-signal"] == "hit_broken"
    assert r2.headers["x-atlas-worker-id"] != owner
    assert "load_gate" in r2.headers["x-atlas-route-reason"].lower()


def test_loads_return_to_zero_after_non_stream(tmp_path: Path):
    app, _fake = _app(tmp_path, "least_load")
    client = TestClient(app)

    res = _chat(client, "hello")
    assert res.status_code == 200
    assert all(v == 0 for v in app.state.loads.values()) or app.state.loads == {}


def test_stream_path_decrements_load(tmp_path: Path):
    app, _fake = _app(tmp_path, "least_load")
    client = TestClient(app)

    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-atlas-demo-key"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": "stream me"},
            ],
            "stream": True,
        },
    ) as res:
        assert res.status_code == 200
        _ = "".join(res.iter_text())

    assert all(v == 0 for v in app.state.loads.values()) or app.state.loads == {}


def test_in_flight_load_visible_during_slow_upstream(tmp_path: Path):
    """While upstream runs, loads[worker] >= 1 so least_load can see pressure."""
    from app import create_app

    seen: dict[str, int] = {}

    class SlowFake:
        last_timings = {
            "request_id": "chatcmpl-slow",
            "ttft_ms": None,
            "completion_ms": 1.0,
            "status": "ok",
            "tokens_per_s": None,
        }

        def chat_completions(self, payload: dict) -> dict:
            # Capture loads mid-request via closure on app — set after create
            seen.update(dict(app.state.loads))
            return {
                "id": "chatcmpl-slow",
                "object": "chat.completion",
                "model": MODEL,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
            }

    app = create_app(
        tenants_path=_tenants_yaml(tmp_path / "tenants.yaml"),
        workers_path=_workers_yaml(tmp_path / "workers.yaml"),
        strategy="least_load",
        worker_client_factory=lambda _url: SlowFake(),
    )
    client = TestClient(app)
    res = _chat(client, "probe")
    assert res.status_code == 200
    assert any(v >= 1 for v in seen.values()), f"expected in-flight load, got {seen}"
    assert all(v == 0 for v in app.state.loads.values()) or app.state.loads == {}
