"""Phase 5: fake worker latency + matrix harness (AC-006–007)."""

from __future__ import annotations

from pathlib import Path


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
        assert "ttft_p50_ms" in row
        assert "cache_hit_pct" in row
        text = out.read_text(encoding="utf-8")
        assert row["strategy"] in text
