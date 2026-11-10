"""Measure what recording adds to gateway latency (in-process ASGI, instant fake upstream).

Run:  python benchmarks/recorder_overhead.py [concurrent_runs] [steps]

This isolates the gateway + SQLite commit cost. It does not include network or a real model,
so treat the numbers as the recorder's own overhead, not end-to-end latency.
"""

from __future__ import annotations

import asyncio
import statistics
import sys
import tempfile
import time
from pathlib import Path

import httpx

MODEL = "bench-model"


class InstantUpstream:
    async def chat_completions(self, payload, stats):
        stats.update(request_id="b", ttft_ms=None, completion_ms=0.1, status="ok", tokens_per_s=None)
        return {"id": "b", "object": "chat.completion",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}]}

    async def stream_chat_completions(self, payload, stats):
        raise AssertionError("not used")
        yield  # pragma: no cover


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


async def _run_mode(app, mode: str, concurrent_runs: int, steps: int) -> dict:
    latencies: list[float] = []
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://bench") as client:

        async def one_run(i: int) -> None:
            for s in range(steps):
                headers = {"Authorization": "Bearer sk-bench"}
                if mode == "record":
                    headers.update({"x-atlas-mode": "record", "x-atlas-run-id": f"{mode}-{i}",
                                    "x-atlas-step": str(s)})
                t0 = time.perf_counter()
                res = await client.post(
                    "/v1/chat/completions", headers=headers,
                    json={"model": MODEL, "messages": [{"role": "user", "content": f"run{i} step{s}"}]},
                )
                latencies.append((time.perf_counter() - t0) * 1000)
                assert res.status_code == 200, res.text

        await asyncio.gather(*(one_run(i) for i in range(concurrent_runs)))
    return {
        "requests": len(latencies),
        "p50_ms": round(_percentile(latencies, 0.50), 3),
        "p95_ms": round(_percentile(latencies, 0.95), 3),
        "max_ms": round(max(latencies), 3),
        "mean_ms": round(statistics.mean(latencies), 3),
    }


async def measure(workdir: Path, concurrent_runs: int = 50, steps: int = 3) -> dict:
    from app import create_app
    from recorder import Recorder

    tenants = workdir / "tenants.yaml"
    tenants.write_text(
        f"tenants:\n  - id: bench\n    api_key: sk-bench\n    rpm_limit: 1000000\n"
        f"    record_allowed: true\n    allowed_models: [{MODEL}]\n",
        encoding="utf-8",
    )
    workers = workdir / "workers.yaml"
    workers.write_text(
        f"workers:\n  - id: w\n    model: {MODEL}\n    base_url: http://bench/v1\n", encoding="utf-8"
    )
    recorder = Recorder(workdir / "bench-runs.db")
    app = create_app(tenants_path=tenants, workers_path=workers,
                     worker_client_factory=lambda _u: InstantUpstream(), recorder=recorder)
    try:
        live = await _run_mode(app, "live", concurrent_runs, steps)
        record = await _run_mode(app, "record", concurrent_runs, steps)
    finally:
        recorder.close()
    return {
        "concurrent_runs": concurrent_runs,
        "live": live,
        "record": record,
        "added_p50_ms": round(record["p50_ms"] - live["p50_ms"], 3),
        "added_p95_ms": round(record["p95_ms"] - live["p95_ms"], 3),
    }


if __name__ == "__main__":
    import json

    root = Path(__file__).resolve().parents[1]
    for sub in ("platform/gateway", "platform/tenant", "platform/registry", "platform/router",
                "platform/observability", "platform/recorder", "workers"):
        sys.path.insert(0, str(root / sub))
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    steps = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    with tempfile.TemporaryDirectory() as tmp:
        print(json.dumps(asyncio.run(measure(Path(tmp), runs, steps)), indent=2))
