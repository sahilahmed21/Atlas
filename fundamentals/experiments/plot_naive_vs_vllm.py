"""Phase 3 — overlay Phase 1 naive HF vs Phase 3 vLLM latency curves.

Reads two CSVs with the Phase 1 schema; writes results/phase3/naive_vs_vllm.png.
Does not invent rows — missing CSVs raise.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402 — backend must be set first

from plot_failure_curve import load_runs

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NAIVE = ROOT / "results" / "phase1" / "naive_load.csv"
DEFAULT_VLLM = ROOT / "results" / "phase3" / "vllm_load.csv"
DEFAULT_OUT = ROOT / "results" / "phase3" / "naive_vs_vllm.png"


def pair_by_concurrency(
    naive_csv: Path,
    vllm_csv: Path,
    max_new_tokens: int = 32,
) -> list[dict]:
    """Join ok rows that share n_concurrent for the given max_new_tokens."""
    if not Path(vllm_csv).is_file():
        raise FileNotFoundError(vllm_csv)
    if not Path(naive_csv).is_file():
        raise FileNotFoundError(naive_csv)

    naive = {
        r["n_concurrent"]: r
        for r in load_runs(naive_csv)
        if r["max_new_tokens"] == max_new_tokens
        and r["status"] == "ok"
        and r["total_ms"] is not None
    }
    vllm = {
        r["n_concurrent"]: r
        for r in load_runs(vllm_csv)
        if r["max_new_tokens"] == max_new_tokens
        and r["status"] == "ok"
        and r["total_ms"] is not None
    }

    pairs: list[dict] = []
    for n in sorted(set(naive) & set(vllm)):
        pairs.append(
            {
                "n_concurrent": n,
                "naive_total_ms": naive[n]["total_ms"],
                "vllm_total_ms": vllm[n]["total_ms"],
                "naive_peak_vram_mb": naive[n]["peak_vram_mb"],
                "vllm_peak_vram_mb": vllm[n]["peak_vram_mb"],
            }
        )
    return pairs


def plot_overlay(pairs: list[dict], out_path: Path, model: str) -> Path:
    fig, (ax_lat, ax_vram) = plt.subplots(2, 1, figsize=(8, 8), sharex=True)
    xs = [p["n_concurrent"] for p in pairs]

    ax_lat.plot(xs, [p["naive_total_ms"] for p in pairs], marker="o", label="naive HF")
    ax_lat.plot(xs, [p["vllm_total_ms"] for p in pairs], marker="o", label="vLLM")
    ax_lat.set_title(f"Naive HF vs vLLM\n{model}")
    ax_lat.set_ylabel("p50 request latency (ms)")
    ax_lat.grid(alpha=0.3)
    ax_lat.legend(fontsize=8)

    ax_vram.plot(
        xs, [p["naive_peak_vram_mb"] for p in pairs], marker="s", label="naive HF"
    )
    ax_vram.plot(
        xs, [p["vllm_peak_vram_mb"] for p in pairs], marker="s", label="vLLM"
    )
    ax_vram.set_xlabel("concurrent requests (N)")
    ax_vram.set_ylabel("peak VRAM (MB)")
    ax_vram.grid(alpha=0.3)
    ax_vram.legend(fontsize=8)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main() -> int:
    p = argparse.ArgumentParser(description="Plot Phase 3 naive vs vLLM overlay")
    p.add_argument("--naive-csv", type=Path, default=DEFAULT_NAIVE)
    p.add_argument("--vllm-csv", type=Path, default=DEFAULT_VLLM)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--max-new-tokens", type=int, default=32)
    p.add_argument("--model", type=str, default="Qwen/Qwen2.5-0.5B-Instruct")
    args = p.parse_args()

    pairs = pair_by_concurrency(args.naive_csv, args.vllm_csv, args.max_new_tokens)
    if not pairs:
        raise SystemExit("no overlapping ok concurrency points to plot")
    out = plot_overlay(pairs, args.out, args.model)
    print(f"wrote {out} ({len(pairs)} points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
