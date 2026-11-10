"""RED/GREEN Phase 11b: tenants only see their own events; query-string keys are opt-in."""

from pathlib import Path

from fastapi.testclient import TestClient

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
KEY_A = "sk-atlas-a"
KEY_B = "sk-atlas-b"


def _app(tmp_path: Path, **kwargs):
    from app import create_app

    t = tmp_path / "t.yaml"
    t.write_text(
        "tenants:\n"
        f"  - id: a\n    api_key: {KEY_A}\n    rpm_limit: 100\n    allowed_models: [{MODEL}]\n"
        f"  - id: b\n    api_key: {KEY_B}\n    rpm_limit: 100\n    allowed_models: [{MODEL}]\n",
        encoding="utf-8",
    )
    w = tmp_path / "w.yaml"
    w.write_text(
        f"workers:\n  - id: worker-a\n    model: {MODEL}\n    base_url: http://fake/v1\n",
        encoding="utf-8",
    )

    class Fake:
        async def chat_completions(self, payload, stats):
            stats.update(
                request_id="x", ttft_ms=None, completion_ms=1.0, status="ok", tokens_per_s=None
            )
            return {"id": "x", "object": "chat.completion", "choices": []}

        async def stream_chat_completions(self, payload, stats):
            raise AssertionError("not used")
            yield  # pragma: no cover

    return create_app(
        tenants_path=t, workers_path=w, worker_client_factory=lambda _u: Fake(), **kwargs
    )


def _chat(client: TestClient, key: str):
    res = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": MODEL, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert res.status_code == 200


def test_snapshot_returns_only_the_callers_events(tmp_path: Path):
    client = TestClient(_app(tmp_path))
    _chat(client, KEY_A)
    _chat(client, KEY_A)
    _chat(client, KEY_B)

    a = client.get("/atlas/snapshot", headers={"Authorization": f"Bearer {KEY_A}"}).json()
    b = client.get("/atlas/snapshot", headers={"Authorization": f"Bearer {KEY_B}"}).json()

    assert [e["tenant_id"] for e in a["events"]] == ["a", "a"]
    assert [e["tenant_id"] for e in b["events"]] == ["b"]


def test_event_stream_catchup_returns_only_the_callers_events(tmp_path: Path):
    client = TestClient(_app(tmp_path))
    _chat(client, KEY_A)
    _chat(client, KEY_B)

    with client.stream(
        "GET",
        "/atlas/events?catchup_only=true",
        headers={"Authorization": f"Bearer {KEY_B}"},
    ) as res:
        text = "".join(res.iter_text())

    assert '"tenant_id": "b"' in text
    assert '"tenant_id": "a"' not in text


def test_query_string_key_is_rejected_by_default(tmp_path: Path):
    client = TestClient(_app(tmp_path))

    assert client.get(f"/atlas/snapshot?api_key={KEY_A}").status_code == 401


def test_query_string_key_works_when_demo_flag_enabled(tmp_path: Path):
    client = TestClient(_app(tmp_path, allow_query_key=True))
    _chat(client, KEY_A)

    res = client.get(f"/atlas/snapshot?api_key={KEY_A}")

    assert res.status_code == 200
    assert len(res.json()["events"]) == 1


def test_authenticate_tolerates_non_ascii_and_wrong_length_keys():
    from tenants import Tenant, authenticate

    tenants = [Tenant(id="a", api_key=KEY_A, rpm_limit=1, allowed_models=[])]

    assert authenticate(tenants, "sk-é-unicode") is None
    assert authenticate(tenants, "x") is None
    assert authenticate(tenants, KEY_A).id == "a"
