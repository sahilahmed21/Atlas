"""Phase 1 — plot the naive HF failure curve from the load sweep CSV.

Reads results/phase1/naive_load.csv, writes results/phase1/oom_latency_curve.png.

Protocol: docs/phases/phase-1/02_naive_baseline.md
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402 — backend must be set first

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "results" / "phase1" / "naive_load.csv"
DEFAULT_OUT = ROOT / "results" / "phase1" / "oom_latency_curve.png"

INT_FIELDS = ("n_concurrent", "prompt_tokens", "max_new_tokens")
FLOAT_FIELDS = ("ttft_ms", "total_ms", "tokens_per_s", "peak_vram_mb")


def load_runs(csv_path: Path) -> list[dict]:
    """Parse the sweep CSV into numeric rows sorted by concurrency."""
    runs: list[dict] = []
    with Path(csv_path).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            run = dict(row)
            for field in INT_FIELDS:
                run[field] = int(row[field]) if row.get(field) else None
            for field in FLOAT_FIELDS:
                run[field] = float(row[field]) if row.get(field) else None
            runs.append(run)
    return sorted(runs, key=lambda r: (r["max_new_tokens"] or 0, r["n_concurrent"] or 0))


def mark_failures(runs: list[dict], cliff_factor: float = 5.0) -> list[dict]:
    """Tag each run as 'oom', 'cliff', or None.

    A cliff is only claimed relative to a measured N=1 baseline for the same
    max_new_tokens — without that baseline there is nothing honest to compare to.
    """
    baselines = {
        run["max_new_tokens"]: run["total_ms"]
        for run in runs
        if run["n_concurrent"] == 1 and run["status"] == "ok" and run["total_ms"]
    }

    for run in runs:
        baseline = baselines.get(run["max_new_tokens"])
        if run["status"] == "oom":
            run["failure"] = "oom"
        elif (
            baseline
            and run["total_ms"]
            and run["n_concurrent"] != 1
            and run["total_ms"] > cliff_factor * baseline
        ):
            run["failure"] = "cliff"
        else:
            run["failure"] = None
    return runs


def plot(runs: list[dict], out_path: Path, cliff_factor: float = 5.0) -> Path:
    series = defaultdict(list)
    for run in runs:
        series[run["max_new_tokens"]].append(run)

    hardware = runs[0]["hardware"]
    model = runs[0]["model"]

    fig, (ax_lat, ax_vram) = plt.subplots(2, 1, figsize=(8, 8), sharex=True)

    for max_new_tokens, rows in sorted(series.items()):
        ok = [r for r in rows if r["total_ms"]]
        ax_lat.plot(
            [r["n_concurrent"] for r in ok],
            [r["total_ms"] for r in ok],
            marker="o",
            label=f"max_new_tokens={max_new_tokens}",
        )
        ax_vram.plot(
            [r["n_concurrent"] for r in rows],
            [r["peak_vram_mb"] for r in rows],
            marker="s",
            label=f"max_new_tokens={max_new_tokens}",
        )

        baseline = next(
            (r["total_ms"] for r in rows if r["n_concurrent"] == 1 and r["total_ms"]),
            None,
        )
        if baseline:
            ax_lat.axhline(
                cliff_factor * baseline,
                linestyle=":",
                color="grey",
                label=f"{cliff_factor:g}x N=1 baseline",
            )

    cliffs = [r for r in runs if r["failure"] == "cliff"]
    ooms = [r for r in runs if r["failure"] == "oom"]
    if cliffs:
        ax_lat.scatter(
            [r["n_concurrent"] for r in cliffs],
            [r["total_ms"] for r in cliffs],
            s=220,
            facecolors="none",
            edgecolors="darkorange",
            linewidths=2.5,
            zorder=5,
            label="latency cliff",
        )
    for run in ooms:
        ax_lat.axvline(run["n_concurrent"], color="red", linestyle="--", alpha=0.7)
        ax_lat.annotate(
            "OOM",
            xy=(run["n_concurrent"], ax_lat.get_ylim()[1]),
            color="red",
            ha="center",
            va="top",
            fontweight="bold",
        )

    ax_lat.set_title(f"Naive HF generate() failure curve\n{model} · fp16 · {hardware}")
    ax_lat.set_ylabel("p50 request latency (ms)")
    ax_lat.grid(alpha=0.3)
    ax_lat.legend(fontsize=8)

    ax_vram.set_xlabel("concurrent requests (N)")
    ax_vram.set_ylabel("peak VRAM (MB)")
    ax_vram.grid(alpha=0.3)
    ax_vram.legend(fontsize=8)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot Phase 1 failure curve")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cliff-factor", type=float, default=5.0)
    args = parser.parse_args()

    runs = mark_failures(load_runs(args.csv), args.cliff_factor)
    plot(runs, args.out, args.cliff_factor)

    for run in runs:
        print(
            f"N={run['n_concurrent']:<3} total_ms={run['total_ms']} "
            f"peak_vram_mb={run['peak_vram_mb']} failure={run['failure']}"
        )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
