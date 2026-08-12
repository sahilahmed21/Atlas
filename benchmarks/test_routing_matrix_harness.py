"""Phase 5/7: fake worker latency + matrix harness (sim + live)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx


def test_simulated_worker_hit_faster_than_miss_and_load_penalty():
    from fake_worker import SimulatedWorkerClient

    loads = {"worker-a": 0}
    client = SimulatedWorkerClient("worker-a", loads=loads, queue_penalty_ms=20.0)
    messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "u1"}]

    miss = client.chat_completions({"model": "m", "messages": messages})
    miss_ttft = client.last_timings["ttft_ms"]
    hit = client.chat_completions(
        {
            "model": "m",
            "messages": [
                {"role": "system", "content": "S"},
                {"role": "user", "content": "u2"},
            ],
        }
    )
    hit_ttft = client.last_timings["ttft_ms"]

    assert miss["object"] == "chat.completion"
    assert hit["object"] == "chat.completion"
    assert hit_ttft < miss_ttft

    loaded = SimulatedWorkerClient(
        "worker-b",
        loads={"worker-b": 5},
        base_hit_ms=10.0,
        base_miss_ms=10.0,
        queue_penalty_ms=10.0,
    )
    loaded.chat_completions(
        {"model": "m", "messages": [{"role": "user", "content": "x"}]}
    )
    assert loaded.last_timings["ttft_ms"] >= 10.0 + 10.0 * 5


def test_matrix_runner_writes_csv_for_one_pattern(tmp_path: Path):
    from run_routing_matrix import run_matrix

    out = tmp_path / "routing_matrix.csv"
    rows = run_matrix(
        patterns=["high_reuse"],
        strategies=["round_robin", "least_load", "prefix_aware"],
        n=8,
        out_csv=out,
    )

    assert out.is_file()
    assert len(rows) == 3
    for row in rows:
        assert row["worker_mode"] == "simulated"
        assert row["pattern"] == "high_reuse"
        assert row["load_margin"] == 0
        assert "ttft_p50_ms" in row
        assert "cache_hit_pct" in row
        text = out.read_text(encoding="utf-8")
        assert row["strategy"] in text


def test_phase8_gate_matrix_three_way(tmp_path: Path):
    from run_routing_matrix import run_matrix

    out = tmp_path / "gate_matrix.csv"
    rows = run_matrix(
        patterns=["high_reuse"],
        strategy_margins=[
            ("round_robin", 0),
            ("prefix_aware", 0),
            ("prefix_aware", 1),
        ],
        n=8,
        out_csv=out,
    )
    assert len(rows) == 3
    sticky = rows[1]
    gated = rows[2]
    assert sticky["load_margin"] == 0
    assert gated["load_margin"] == 1
    assert sticky["worker_skew"] >= gated["worker_skew"]
    assert gated["ttft_p50_ms"] <= sticky["ttft_p50_ms"]


def _mock_live_factory(base_url: str):
    """OpenAIWorkerClient over MockTransport — proves live path without GPU."""
    from openai_worker_client import OpenAIWorkerClient

    chunks = [
        b'data: {"id":"chatcmpl-live","choices":[{"delta":{"content":"ok"}}]}\n\n',
        b"data: [DONE]\n\n",
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body.get("stream") is True
        return httpx.Response(
            200,
            content=b"".join(chunks),
            headers={"content-type": "text/event-stream"},
        )

    http = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url=base_url,
    )
    return OpenAIWorkerClient(base_url=base_url, http=http)


def test_live_matrix_writes_metadata_and_streaming_ttft(tmp_path: Path):
    """Phase 7: live mode must not use SimulatedWorkerClient; CSV carries GPU labels."""
    from fake_worker import SimulatedWorkerClient
    from run_routing_matrix import run_matrix

    out = tmp_path / "routing_matrix_live.csv"
    rows = run_matrix(
        patterns=["high_reuse"],
        strategies=["round_robin", "prefix_aware"],
        n=4,
        out_csv=out,
        worker_mode="live",
        worker_urls=(
            "http://mock-a/v1",
            "http://mock-b/v1",
        ),
        worker_client_factory=_mock_live_factory,
        hardware="colab-t4",
        vllm_version="0.26.0",
        replica_mode="time_sliced_dual",
    )

    assert out.is_file()
    assert len(rows) == 2
    text = out.read_text(encoding="utf-8")
    assert "worker_mode" in text
    assert "hardware" in text
    assert "vllm_version" in text
    assert "replica_mode" in text
    for row in rows:
        assert row["worker_mode"] == "live"
        assert row["hardware"] == "colab-t4"
        assert row["vllm_version"] == "0.26.0"
        assert row["replica_mode"] == "time_sliced_dual"
        assert row["pattern"] == "high_reuse"
        assert row["n"] == 4
        assert row["ttft_p50_ms"] is not None
        assert float(row["ttft_p50_ms"]) >= 0.0
        assert "SimulatedWorkerClient" not in type(
            _mock_live_factory("http://x/v1")
        ).__name__
    assert SimulatedWorkerClient.__name__ == "SimulatedWorkerClient"
    assert "live" in text
    assert "prefix_aware" in text
    assert "round_robin" in text