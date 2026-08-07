"""RED/GREEN: review fixes — RPM race, worker errors, metrics auth, 400 validation."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry


MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def _tenants(path: Path, rpm: int = 60) -> Path:
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


def test_try_acquire_is_atomic_under_threads():
    from rpm import ProcessLocalRPMLimiter

    lim = ProcessLocalRPMLimiter(clock=lambda: 0.0)
    allowed = []

    def once():
        allowed.append(lim.try_acquire("demo", limit=10))

    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(lambda _: once(), range(20)))

    assert sum(1 for x in allowed if x) == 10
    assert sum(1 for x in allowed if not x) == 10


def test_worker_http_error_returns_openai_shaped_502(tmp_path: Path):
    from app import create_app

    class BoomWorker:
        last_timings = {"status": "error", "completion_ms": 1.0}

        def chat_completions(self, payload):
            req = httpx.Request("POST", "http://fake/v1/chat/completions")
            resp = httpx.Response(503, request=req, json={"error": {"message": "down"}})
            raise httpx.HTTPStatusError("down", request=req, response=resp)

        def stream_chat_completions(self, payload):
            raise AssertionError("not used")

    app = create_app(
        tenants_path=_tenants(tmp_path / "t.yaml"),
        workers_path=_workers(tmp_path / "w.yaml"),
        worker_client_factory=lambda _u: BoomWorker(),
    )
    client = TestClient(app, raise_server_exceptions=False)
    res = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer sk-atlas-demo-key"},
        json={"model": MODEL, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert res.status_code == 502
    err = res.json()["error"]
    assert "message" in err
    assert err.get("type") == "upstream_error"


def test_metrics_requires_auth(tmp_path: Path):
    from app import create_app
    from atlas_metrics import AtlasMetrics

    class OkWorker:
        last_timings = {
            "request_id": "x",
            "ttft_ms": None,
            "completion_ms": 1.0,
            "status": "ok",
            "tokens_per_s": None,
        }

        def chat_completions(self, payload):
            return {
                "id": "x",
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
            yield "data: [DONE]\n\n"

    app = create_app(
        tenants_path=_tenants(tmp_path / "t.yaml"),
        workers_path=_workers(tmp_path / "w.yaml"),
        worker_client_factory=lambda _u: OkWorker(),
        metrics=AtlasMetrics(registry=CollectorRegistry()),
    )
    client = TestClient(app)
    assert client.get("/metrics").status_code == 401
    ok = client.get(
        "/metrics",
        headers={"Authorization": "Bearer sk-atlas-demo-key"},
    )
    assert ok.status_code == 200
    assert "atlas_queue_depth" in ok.text


def test_invalid_json_body_returns_400_openai_shape(tmp_path: Path):
    from app import create_app

    class OkWorker:
        def chat_completions(self, payload):
            return {"id": "x", "object": "chat.completion", "choices": []}

        def stream_chat_completions(self, payload):
            yield "data: [DONE]\n\n"

    app = create_app(
        tenants_path=_tenants(tmp_path / "t.yaml"),
        workers_path=_workers(tmp_path / "w.yaml"),
        worker_client_factory=lambda _u: OkWorker(),
    )
    client = TestClient(app)
    res = client.post(
        "/v1/chat/completions",
        headers={
            "Authorization": "Bearer sk-atlas-demo-key",
            "Content-Type": "application/json",
        },
        content=b'{"model": 123, "messages": "nope"}',
    )
    assert res.status_code == 400
    assert "error" in res.json()
    assert "message" in res.json()["error"]


def test_round_robin_safe_under_threads():
    from types import SimpleNamespace
    from strategies import RoundRobinRouter

    router = RoundRobinRouter()
    workers = [
        SimpleNamespace(id="a"),
        SimpleNamespace(id="b"),
        SimpleNamespace(id="c"),
    ]
    picks = []

    def once():
        picks.append(router.choose(workers).worker_id)

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(lambda _: once(), range(30)))

    assert sorted(picks) == sorted(["a", "b", "c"] * 10)


def test_client_cache_reuses_same_instance(tmp_path: Path):
    from app import create_app

    created = []

    class OkWorker:
        last_timings = {
            "request_id": "x",
            "ttft_ms": None,
            "completion_ms": 1.0,
            "status": "ok",
            "tokens_per_s": None,
        }

        def chat_completions(self, payload):
            return {
                "id": "x",
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
            yield "data: [DONE]\n\n"

        def close(self):
            pass

    def factory(url):
        w = OkWorker()
        created.append(url)
        return w

    app = create_app(
        tenants_path=_tenants(tmp_path / "t.yaml"),
        workers_path=_workers(tmp_path / "w.yaml"),
        worker_client_factory=factory,
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer sk-atlas-demo-key"}
    body = {"model": MODEL, "messages": [{"role": "user", "content": "hi"}]}
    assert client.post("/v1/chat/completions", headers=headers, json=body).status_code == 200
    assert client.post("/v1/chat/completions", headers=headers, json=body).status_code == 200
    assert len(created) == 1
