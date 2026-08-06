"""Phase 3 — vLLM concurrent load sweep (same CSV contract as Phase 1).

Offline-testable helpers live here. The GPU path (LLM.generate) runs on
Colab/Kaggle/WSL after `uv sync --group gpu` (or the +cu129 wheel on T4).

Protocol: docs/phases/phase-3/README.md
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs" / "models" / "phase3.yaml"
DEFAULT_OUT = ROOT / "results" / "phase3" / "vllm_load.csv"

PINNED_VLLM_VERSION = "0.26.0"

CSV_FIELDS = [
    "timestamp",
    "hardware",
    "model",
    "n_concurrent",
    "prompt_tokens",
    "max_new_tokens",
    "ttft_ms",
    "total_ms",
    "tokens_per_s",
    "peak_vram_mb",
    "status",
    "notes",
]


def load_config(path: Path) -> dict:
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def assert_runtime_vllm_matches_pin(runtime_version: str) -> None:
    if runtime_version != PINNED_VLLM_VERSION:
        raise RuntimeError(
            f"runtime vLLM {runtime_version!r} != pinned {PINNED_VLLM_VERSION!r}"
        )


def build_row(
    *,
    hardware: str,
    model: str,
    n_concurrent: int,
    prompt_tokens: int,
    max_new_tokens: int,
    ttft_ms: float | None,
    total_ms: float | None,
    tokens_per_s: float | None,
    peak_vram_mb: float | None,
    status: str,
    notes: str,
    timestamp: str | None = None,
) -> dict:
    note = notes.strip()
    pin = f"vllm={PINNED_VLLM_VERSION}"
    if pin not in note:
        note = f"{note}; {pin}" if note else pin
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "timestamp": ts,
        "hardware": hardware,
        "model": model,
        "n_concurrent": n_concurrent,
        "prompt_tokens": prompt_tokens,
        "max_new_tokens": max_new_tokens,
        "ttft_ms": f"{ttft_ms:.3f}" if ttft_ms is not None else "",
        "total_ms": f"{total_ms:.3f}" if total_ms is not None else "",
        "tokens_per_s": f"{tokens_per_s:.3f}" if tokens_per_s is not None else "",
        "peak_vram_mb": f"{peak_vram_mb:.1f}" if peak_vram_mb is not None else "",
        "status": status,
        "notes": note,
    }


def append_csv(path: Path, row: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


def peak_vram_mb() -> float | None:
    try:
        import torch
    except ImportError:
        return None
    if not torch.cuda.is_available():
        return None
    return torch.cuda.max_memory_allocated() / (1024**2)


def reset_peak_vram() -> None:
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()


def one_generate(llm, prompt: str, max_new_tokens: int) -> dict:
    """Single offline LLM.generate(); TTFT recorded as total (proxy)."""
    from vllm import SamplingParams

    params = SamplingParams(max_tokens=max_new_tokens, temperature=0.0)
    t0 = time.perf_counter()
    outputs = llm.generate([prompt], params)
    total_ms = (time.perf_counter() - t0) * 1000.0
    out = outputs[0]
    prompt_tokens = len(out.prompt_token_ids)
    new_tokens = max(len(out.outputs[0].token_ids), 1)
    return {
        "prompt_tokens": prompt_tokens,
        "total_ms": total_ms,
        "ttft_ms": total_ms,  # ponytail: no streaming hook; document as proxy
        "tokens_per_s": new_tokens / (total_ms / 1000.0),
        "new_tokens": new_tokens,
    }


def run_concurrent(llm, prompt: str, n: int, max_new_tokens: int) -> dict:
    reset_peak_vram()
    errors: list[str] = []
    totals: list[float] = []
    prompt_tokens = 0
    tok_rates: list[float] = []

    def worker(_: int) -> dict:
        return one_generate(llm, prompt, max_new_tokens)

    try:
        with ThreadPoolExecutor(max_workers=n) as pool:
            futs = [pool.submit(worker, i) for i in range(n)]
            for fut in as_completed(futs):
                metrics = fut.result()
                totals.append(metrics["total_ms"])
                tok_rates.append(metrics["tokens_per_s"])
                prompt_tokens = metrics["prompt_tokens"]
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{type(exc).__name__}: {exc}")
        text = str(exc).lower()
        status = "oom" if "out of memory" in text or "cuda" in text and "memory" in text else "error"
        return {
            "prompt_tokens": prompt_tokens,
            "ttft_ms": None,
            "total_ms": None,
            "tokens_per_s": None,
            "peak_vram_mb": peak_vram_mb(),
            "status": status,
            "notes": "; ".join(errors),
        }

    # p50 of per-request totals (same philosophy as Phase 1 concurrent wall)
    totals_sorted = sorted(totals)
    mid = totals_sorted[len(totals_sorted) // 2]
    return {
        "prompt_tokens": prompt_tokens,
        "ttft_ms": mid,
        "total_ms": mid,
        "tokens_per_s": sum(tok_rates) / len(tok_rates),
        "peak_vram_mb": peak_vram_mb(),
        "status": "ok",
        "notes": "ttft_proxy=total",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="vLLM concurrent load sweep (Phase 3)")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--n-only", type=int, default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config)

    pinned = str(cfg.get("vllm_version", PINNED_VLLM_VERSION))
    if pinned != PINNED_VLLM_VERSION:
        print(
            f"config vllm_version={pinned!r} != harness pin {PINNED_VLLM_VERSION!r}",
            file=sys.stderr,
        )
        return 2

    try:
        import vllm
        from vllm import LLM
    except ImportError as exc:
        print(
            "vLLM not installed. On Colab/Kaggle T4 (CUDA 12.x drivers) prefer:\n"
            "  pip install "
            "https://github.com/vllm-project/vllm/releases/download/v0.26.0/"
            "vllm-0.26.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl\n"
            "Else: uv sync --group gpu  (Linux; default wheel may need CUDA 13)",
            file=sys.stderr,
        )
        print(exc, file=sys.stderr)
        return 2

    assert_runtime_vllm_matches_pin(vllm.__version__)

    model = cfg.get("hub_model_id") or cfg.get("model_id")
    revision = cfg.get("revision", "main")
    dtype = cfg.get("dtype", "float16")
    prompt = cfg["prompt_template"]
    hardware = cfg.get("hardware_label", "colab-t4")
    cliff_factor = float(cfg.get("cliff_factor", 5.0))
    max_new_tokens_sweep = list(cfg.get("max_new_tokens_sweep", [32]))
    concurrency_sweep = list(cfg.get("concurrency_sweep", [1, 2, 4, 8]))
    if args.n_only is not None:
        concurrency_sweep = [args.n_only]
        max_new_tokens_sweep = max_new_tokens_sweep[:1]

    print(
        f"vllm={vllm.__version__} model={model} rev={revision[:12]} dtype={dtype}",
        flush=True,
    )
    llm = LLM(model=model, revision=revision, dtype=dtype, trust_remote_code=False)

    baseline_n1_ms: dict[int, float] = {}
    stop_sweep = False
    for max_new_tokens in max_new_tokens_sweep:
        if stop_sweep:
            break
        for n in concurrency_sweep:
            print(f"run n={n} max_new_tokens={max_new_tokens} …", flush=True)
            try:
                metrics = run_concurrent(llm, prompt, n, max_new_tokens)
            except Exception as exc:  # noqa: BLE001
                traceback.print_exc()
                metrics = {
                    "prompt_tokens": 0,
                    "ttft_ms": None,
                    "total_ms": None,
                    "tokens_per_s": None,
                    "peak_vram_mb": peak_vram_mb(),
                    "status": "error",
                    "notes": f"{type(exc).__name__}: {exc}",
                }

            if n == 1 and metrics["total_ms"] is not None and metrics["status"] == "ok":
                baseline_n1_ms[max_new_tokens] = metrics["total_ms"]

            notes = metrics["notes"]
            baseline = baseline_n1_ms.get(max_new_tokens)
            hit_cliff = (
                baseline is not None
                and metrics["total_ms"] is not None
                and n > 1
                and metrics["status"] == "ok"
                and metrics["total_ms"] > cliff_factor * baseline
            )
            if hit_cliff:
                notes = f"{notes}; latency_cliff>{cliff_factor}x_n1; cliff_stop=1"

            row = build_row(
                hardware=hardware,
                model=model,
                n_concurrent=n,
                prompt_tokens=metrics["prompt_tokens"],
                max_new_tokens=max_new_tokens,
                ttft_ms=metrics["ttft_ms"],
                total_ms=metrics["total_ms"],
                tokens_per_s=metrics["tokens_per_s"],
                peak_vram_mb=metrics["peak_vram_mb"],
                status=metrics["status"],
                notes=notes,
            )
            append_csv(args.out, row)
            print(
                f"  status={row['status']} total_ms={row['total_ms']} "
                f"peak_vram_mb={row['peak_vram_mb']}",
                flush=True,
            )
            if metrics["status"] == "oom" or hit_cliff:
                stop_sweep = True
                break

    print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
