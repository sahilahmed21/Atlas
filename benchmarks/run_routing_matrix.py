"""Replay frozen traffic traces across routing strategies; write Phase 5/7 CSV."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path
from typing import Any, Callable

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
DEFAULT_LIVE_OUT = ROOT / "results" / "phase5-live" / "routing_matrix_live.csv"
DEFAULT_PHASE8_OUT = ROOT / "results" / "phase8" / "gate_matrix.csv"
AUTH = "Bearer sk-atlas-demo-key"
STRATEGIES = ("round_robin", "least_load", "prefix_aware")
PATTERNS = ("high_reuse", "low_reuse", "bursty", "steady")
DEFAULT_LIVE_URLS = (
    "http://127.0.0.1:8001/v1",
    "http://127.0.0.1:8002/v1",
)
SIM_FIELDNAMES = [
    "pattern",
    "strategy",
    "n",
    "ttft_p50_ms",
    "ttft_p95_ms",
    "tokens_per_s_mean",
    "cache_hit_pct",
    "hit_broken_pct",
    "worker_skew",
    "worker_counts",
    "worker_mode",
    "load_margin",
]
LIVE_FIELDNAMES = [
    "pattern",
    "strategy",
    "n",
    "ttft_p50_ms",
    "ttft_p95_ms",
    "tokens_per_s_mean",
    "cache_hit_pct",
    "hit_broken_pct",
    "worker_skew",
    "worker_counts",
    "worker_mode",
    "load_margin",
    "hardware",
    "vllm_version",
    "replica_mode",
    "model",
]


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


def _write_configs(
    tmp: Path,
    *,
    url_a: str = "http://sim-a/v1",
    url_b: str = "http://sim-b/v1",
) -> tuple[Path, Path, dict[str, str]]:
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
        f"    base_url: {url_a}\n"
        "  - id: worker-b\n"
        f"    model: {MODEL}\n"
        f"    base_url: {url_b}\n",
        encoding="utf-8",
    )
    url_to_id = {url_a.rstrip("/"): "worker-a", url_b.rstrip("/"): "worker-b"}
    return tenants, workers, url_to_id


def _run_cell(
    *,
    strategy: str,
    pattern: str,
    n: int,
    tmp: Path,
    worker_mode: str = "simulated",
    worker_urls: tuple[str, str] = DEFAULT_LIVE_URLS,
    worker_client_factory: Callable[[str], Any] | None = None,
    hardware: str = "",
    vllm_version: str = "",
    replica_mode: str = "",
    load_margin: int = 0,
) -> dict[str, Any]:
    from app import create_app
    from openai_worker_client import OpenAIWorkerClient

    cell_dir = tmp / f"{strategy}_{pattern}_m{load_margin}"
    cell_dir.mkdir(parents=True, exist_ok=True)
    if worker_mode == "live":
        tenants, workers_path, url_to_id = _write_configs(
            cell_dir, url_a=worker_urls[0], url_b=worker_urls[1]
        )
    else:
        tenants, workers_path, url_to_id = _write_configs(cell_dir)

    loads: dict[str, int] = {}
    clients: dict[str, Any] = {}

    def factory(base_url: str) -> Any:
        key = base_url.rstrip("/")
        if key not in clients:
            if worker_mode == "live":
                if worker_client_factory is not None:
                    clients[key] = worker_client_factory(base_url)
                else:
                    clients[key] = OpenAIWorkerClient(base_url=base_url)
            else:
                clients[key] = SimulatedWorkerClient(
                    url_to_id[key], loads=loads
                )
        return clients[key]

    app = create_app(
        tenants_path=tenants,
        workers_path=workers_path,
        strategy=strategy,
        worker_client_factory=factory,
        loads=loads,
        prefix_owners={},
        load_margin=load_margin,
    )
    client = TestClient(app)
    trace = build_trace(pattern, n)

    ttfts: list[float] = []
    tokens: list[float] = []
    hits = 0
    broken = 0
    cache_n = 0
    worker_counts: dict[str, int] = {}

    for body in trace:
        req = dict(body)
        if worker_mode == "live":
            req["stream"] = True
            with client.stream(
                "POST",
                "/v1/chat/completions",
                headers={"Authorization": AUTH},
                json=req,
            ) as res:
                if res.status_code != 200:
                    raise RuntimeError(
                        f"{strategy}/{pattern} status={res.status_code} "
                        f"{res.read().decode('utf-8', errors='replace')}"
                    )
                _ = "".join(res.iter_text())
                wid = res.headers["x-atlas-worker-id"]
                signal = res.headers.get("x-atlas-cache-signal", "n/a")
        else:
            res = client.post(
                "/v1/chat/completions",
                headers={"Authorization": AUTH},
                json=req,
            )
            if res.status_code != 200:
                raise RuntimeError(
                    f"{strategy}/{pattern} status={res.status_code} {res.text}"
                )
            wid = res.headers["x-atlas-worker-id"]
            signal = res.headers.get("x-atlas-cache-signal", "n/a")

        worker_counts[wid] = worker_counts.get(wid, 0) + 1
        if signal in {"hit", "miss", "hit_broken"}:
            cache_n += 1
            if signal == "hit":
                hits += 1
            if signal == "hit_broken":
                broken += 1

        if worker_mode == "live":
            upstream = None
            for url, c in clients.items():
                if url_to_id.get(url.rstrip("/")) == wid:
                    upstream = c
                    break
            if upstream is None:
                raise RuntimeError(f"no client for worker {wid}")
            ttfts.append(float(upstream.last_timings.get("ttft_ms") or 0.0))
            tps = upstream.last_timings.get("tokens_per_s")
            if tps is not None:
                tokens.append(float(tps))
        else:
            sim = next(c for c in clients.values() if c.worker_id == wid)
            ttfts.append(float(sim.last_timings.get("ttft_ms") or 0.0))
            tps = sim.last_timings.get("tokens_per_s")
            if tps is not None:
                tokens.append(float(tps))

    ttfts_sorted = sorted(ttfts)
    total = sum(worker_counts.values()) or 1
    skew = max(worker_counts.values()) / total if worker_counts else 0.0
    row: dict[str, Any] = {
        "pattern": pattern,
        "strategy": strategy,
        "n": n,
        "ttft_p50_ms": round(_percentile(ttfts_sorted, 0.50), 3),
        "ttft_p95_ms": round(_percentile(ttfts_sorted, 0.95), 3),
        "tokens_per_s_mean": round(statistics.mean(tokens), 3) if tokens else 0.0,
        "cache_hit_pct": round(100.0 * hits / cache_n, 2) if cache_n else 0.0,
        "hit_broken_pct": round(100.0 * broken / cache_n, 2) if cache_n else 0.0,
        "worker_skew": round(skew, 3),
        "worker_counts": dict(sorted(worker_counts.items())),
        "worker_mode": worker_mode,
        "load_margin": load_margin,
    }
    if worker_mode == "live":
        row["hardware"] = hardware
        row["vllm_version"] = vllm_version
        row["replica_mode"] = replica_mode
        row["model"] = MODEL
    return row


def run_matrix(
    *,
    patterns: list[str] | None = None,
    strategies: list[str] | None = None,
    n: int = 24,
    out_csv: Path | None = None,
    tmp: Path | None = None,
    worker_mode: str = "simulated",
    worker_urls: tuple[str, str] = DEFAULT_LIVE_URLS,
    worker_client_factory: Callable[[str], Any] | None = None,
    hardware: str = "colab-t4",
    vllm_version: str = "0.26.0",
    replica_mode: str = "time_sliced_dual",
    load_margin: int = 0,
    strategy_margins: list[tuple[str, int]] | None = None,
) -> list[dict[str, Any]]:
    import tempfile

    if worker_mode not in {"simulated", "live"}:
        raise ValueError(f"unknown worker_mode: {worker_mode}")

    patterns = list(patterns or PATTERNS)
    if strategy_margins is None:
        strategies = list(strategies or STRATEGIES)
        strategy_margins = [(s, load_margin) for s in strategies]
    if out_csv is None:
        out_csv = DEFAULT_LIVE_OUT if worker_mode == "live" else DEFAULT_OUT
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    def _execute(work: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for pattern in patterns:
            frozen = build_trace(pattern, n)
            assert len(frozen) == n
            for strategy, margin in strategy_margins:
                rows.append(
                    _run_cell(
                        strategy=strategy,
                        pattern=pattern,
                        n=n,
                        tmp=work,
                        worker_mode=worker_mode,
                        worker_urls=worker_urls,
                        worker_client_factory=worker_client_factory,
                        hardware=hardware,
                        vllm_version=vllm_version,
                        replica_mode=replica_mode,
                        load_margin=margin,
                    )
                )
        return rows

    if tmp is not None:
        work = Path(tmp)
        work.mkdir(parents=True, exist_ok=True)
        rows = _execute(work)
    else:
        with tempfile.TemporaryDirectory(prefix="atlas_phase5_") as td:
            rows = _execute(Path(td))

    fieldnames = LIVE_FIELDNAMES if worker_mode == "live" else SIM_FIELDNAMES
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Atlas routing matrix harness")
    parser.add_argument(
        "--worker-mode",
        choices=("simulated", "live"),
        default="simulated",
    )
    parser.add_argument("--patterns", default="", help="comma list; default all/min")
    parser.add_argument("--strategies", default="", help="comma list")
    parser.add_argument("--n", type=int, default=24)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--hardware", default="colab-t4")
    parser.add_argument("--vllm-version", default="0.26.0")
    parser.add_argument("--replica-mode", default="time_sliced_dual")
    parser.add_argument("--worker-a-url", default=DEFAULT_LIVE_URLS[0])
    parser.add_argument("--worker-b-url", default=DEFAULT_LIVE_URLS[1])
    parser.add_argument(
        "--load-margin",
        type=int,
        default=0,
        help="prefix load gate margin; 0=off (Phase 5/7 sticky repro)",
    )
    parser.add_argument(
        "--phase8",
        action="store_true",
        help="high_reuse × RR / prefix / prefix+gate → results/phase8/gate_matrix.csv",
    )
    args = parser.parse_args()

    if args.phase8:
        patterns = ["high_reuse"]
        gate_m = args.load_margin if args.load_margin > 0 else 1
        strategy_margins = [
            ("round_robin", 0),
            ("prefix_aware", 0),
            ("prefix_aware", gate_m),
        ]
        out = args.out or DEFAULT_PHASE8_OUT
    else:
        patterns = (
            [p.strip() for p in args.patterns.split(",") if p.strip()]
            if args.patterns
            else (["high_reuse"] if args.worker_mode == "live" else None)
        )
        strategies = (
            [s.strip() for s in args.strategies.split(",") if s.strip()]
            if args.strategies
            else (
                ["round_robin", "prefix_aware"]
                if args.worker_mode == "live"
                else None
            )
        )
        strategy_margins = (
            [(s, args.load_margin) for s in strategies] if strategies else None
        )
        out = args.out

    rows = run_matrix(
        patterns=patterns,
        strategy_margins=strategy_margins,
        n=args.n,
        out_csv=out,
        worker_mode=args.worker_mode,
        worker_urls=(args.worker_a_url, args.worker_b_url),
        hardware=args.hardware,
        vllm_version=args.vllm_version,
        replica_mode=args.replica_mode,
        load_margin=args.load_margin,
    )
    written = out or (
        DEFAULT_PHASE8_OUT
        if args.phase8
        else (DEFAULT_LIVE_OUT if args.worker_mode == "live" else DEFAULT_OUT)
    )
    print(f"wrote {written} ({len(rows)} rows)")
    for row in rows:
        print(
            f"{row['pattern']:12} {row['strategy']:13} m={row['load_margin']} "
            f"p50={row['ttft_p50_ms']} p95={row['ttft_p95_ms']} "
            f"hit%={row['cache_hit_pct']} broken%={row['hit_broken_pct']} "
            f"skew={row['worker_skew']} mode={row['worker_mode']}"
        )


if __name__ == "__main__":
    main()
