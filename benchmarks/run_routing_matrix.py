"""Replay frozen traffic traces across routing strategies; write Phase 5 CSV."""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _p in (
    "platform/router",
    "platform/gateway",
    "platform/tenant",
    "platform/registry",
    "platform/observability",
    "workers",
    "benchmarks",
):
    sys.path.insert(0, str(ROOT / _p))

from fastapi.testclient import TestClient

from fake_worker import SimulatedWorkerClient
from traffic import MODEL, build_trace

DEFAULT_OUT = ROOT / "results" / "phase5" / "routing_matrix.csv"
AUTH = "Bearer sk-atlas-demo-key"
STRATEGIES = ("round_robin", "least_load", "prefix_aware")
PATTERNS = ("high_reuse", "low_reuse", "bursty", "steady")


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _write_configs(tmp: Path) -> tuple[Path, Path, dict[str, str]]:
    tenants = tmp / "tenants.yaml"
    workers = tmp / "workers.yaml"
    tenants.write_text(
        "tenants:\n"
        "  - id: demo\n"
        "    api_key: sk-atlas-demo-key\n"
        "    rpm_limit: 10000\n"
        "    allowed_models:\n"
        f"      - {MODEL}\n",
        encoding="utf-8",
    )
    workers.write_text(
        "workers:\n"
        "  - id: worker-a\n"
        f"    model: {MODEL}\n"
        "    base_url: http://sim-a/v1\n"
        "  - id: worker-b\n"
        f"    model: {MODEL}\n"
        "    base_url: http://sim-b/v1\n",
        encoding="utf-8",
    )
    url_to_id = {"http://sim-a/v1": "worker-a", "http://sim-b/v1": "worker-b"}
    return tenants, workers, url_to_id


def _run_cell(
    *,
    strategy: str,
    pattern: str,
    n: int,
    tmp: Path,
) -> dict[str, Any]:
    from app import create_app

    cell_dir = tmp / f"{strategy}_{pattern}"
    cell_dir.mkdir(parents=True, exist_ok=True)
    tenants, workers_path, url_to_id = _write_configs(cell_dir)
    loads: dict[str, int] = {}
    clients: dict[str, SimulatedWorkerClient] = {}

    def factory(base_url: str) -> SimulatedWorkerClient:
        if base_url not in clients:
            clients[base_url] = SimulatedWorkerClient(
                url_to_id[base_url], loads=loads
            )
        return clients[base_url]

    app = create_app(
        tenants_path=tenants,
        workers_path=workers_path,
        strategy=strategy,
        worker_client_factory=factory,
        loads=loads,
        prefix_owners={},
    )
    client = TestClient(app)
    trace = build_trace(pattern, n)

    ttfts: list[float] = []
    tokens: list[float] = []
    hits = 0
    cache_n = 0
    worker_counts: dict[str, int] = {}

    for body in trace:
        res = client.post(
            "/v1/chat/completions",
            headers={"Authorization": AUTH},
            json=body,
        )
        if res.status_code != 200:
            raise RuntimeError(
                f"{strategy}/{pattern} status={res.status_code} {res.text}"
            )
        wid = res.headers["x-atlas-worker-id"]
        worker_counts[wid] = worker_counts.get(wid, 0) + 1
        signal = res.headers.get("x-atlas-cache-signal", "n/a")
        if signal in {"hit", "miss"}:
            cache_n += 1
            if signal == "hit":
                hits += 1
        sim = next(c for c in clients.values() if c.worker_id == wid)
        ttfts.append(float(sim.last_timings.get("ttft_ms") or 0.0))
        tps = sim.last_timings.get("tokens_per_s")
        if tps is not None:
            tokens.append(float(tps))

    ttfts_sorted = sorted(ttfts)
    total = sum(worker_counts.values()) or 1
    skew = max(worker_counts.values()) / total if worker_counts else 0.0
    return {
        "pattern": pattern,
        "strategy": strategy,
        "n": n,
        "ttft_p50_ms": round(_percentile(ttfts_sorted, 0.50), 3),
        "ttft_p95_ms": round(_percentile(ttfts_sorted, 0.95), 3),
        "tokens_per_s_mean": round(statistics.mean(tokens), 3) if tokens else 0.0,
        "cache_hit_pct": round(100.0 * hits / cache_n, 2) if cache_n else 0.0,
        "worker_skew": round(skew, 3),
        "worker_counts": dict(sorted(worker_counts.items())),
        "worker_mode": "simulated",
    }


def run_matrix(
    *,
    patterns: list[str] | None = None,
    strategies: list[str] | None = None,
    n: int = 24,
    out_csv: Path | None = None,
    tmp: Path | None = None,
) -> list[dict[str, Any]]:
    import tempfile

    patterns = list(patterns or PATTERNS)
    strategies = list(strategies or STRATEGIES)
    out_csv = Path(out_csv or DEFAULT_OUT)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    def _execute(work: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for pattern in patterns:
            frozen = build_trace(pattern, n)
            assert len(frozen) == n
            for strategy in strategies:
                rows.append(
                    _run_cell(strategy=strategy, pattern=pattern, n=n, tmp=work)
                )
        return rows

    if tmp is not None:
        work = Path(tmp)
        work.mkdir(parents=True, exist_ok=True)
        rows = _execute(work)
    else:
        with tempfile.TemporaryDirectory(prefix="atlas_phase5_") as td:
            rows = _execute(Path(td))

    fieldnames = [
        "pattern",
        "strategy",
        "n",
        "ttft_p50_ms",
        "ttft_p95_ms",
        "tokens_per_s_mean",
        "cache_hit_pct",
        "worker_skew",
        "worker_counts",
        "worker_mode",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})
    return rows


def main() -> None:
    rows = run_matrix()
    print(f"wrote {DEFAULT_OUT} ({len(rows)} rows)")
    for row in rows:
        print(
            f"{row['pattern']:12} {row['strategy']:13} "
            f"p50={row['ttft_p50_ms']} p95={row['ttft_p95_ms']} "
            f"hit%={row['cache_hit_pct']} skew={row['worker_skew']}"
        )


if __name__ == "__main__":
    main()
