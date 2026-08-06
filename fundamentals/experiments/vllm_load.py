"""Phase 3 — vLLM concurrent load sweep (same CSV contract as Phase 1).

Concurrency = one offline LLM.generate([p0..pN-1]) so the engine continuous-
batches (not N threaded single-prompt calls). Prompts use Phase 1 unique
suffixes. VRAM is NVML used-bytes (not torch allocator).

Protocol: docs/phases/phase-3/README.md
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs" / "models" / "phase3.yaml"
DEFAULT_OUT = ROOT / "results" / "phase3" / "vllm_load.csv"

PINNED_VLLM_VERSION = "0.26.0"

# Colab/Kaggle T4 with CUDA 12.x drivers — default PyPI 0.26.0 wants CUDA 13.
CU129_WHEEL = (
    "https://github.com/vllm-project/vllm/releases/download/v0.26.0/"
    "vllm-0.26.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl"
)

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


def make_prompts(prompt_template: str, n: int) -> list[str]:
    """Same unique-suffix shape as Phase 1 naive_hf_load.run_concurrent."""
    return [f"{prompt_template} [req={i}]" for i in range(n)]


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
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


def peak_vram_mb() -> float | None:
    """Device memory in use via NVML — vLLM pools bypass torch's allocator."""
    try:
        import pynvml
    except ImportError:
        return None
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return info.used / (1024**2)
    except Exception:  # noqa: BLE001 — no GPU / driver
        return None


def is_oom(exc: BaseException) -> bool:
    if type(exc).__name__ in {"OutOfMemoryError", "TorchCudaOOMError"}:
        return True
    text = f"{type(exc).__name__}: {exc}".lower()
    return "out of memory" in text or "cuda out of memory" in text


def run_concurrent(
    llm,
    prompt_template: str,
    n: int,
    max_new_tokens: int,
    sampling_params=None,
) -> dict:
    """One batched generate() — continuous batching — with Phase 1 unique prompts."""
    prompts = make_prompts(prompt_template, n)
    if sampling_params is None:
        from vllm import SamplingParams

        sampling_params = SamplingParams(max_tokens=max_new_tokens, temperature=0.0)

    try:
        t0 = time.perf_counter()
        outputs = llm.generate(prompts, sampling_params)
        wall_ms = (time.perf_counter() - t0) * 1000.0
    except Exception as exc:  # noqa: BLE001
        return {
            "prompt_tokens": 0,
            "ttft_ms": None,
            "total_ms": None,
            "tokens_per_s": None,
            "peak_vram_mb": peak_vram_mb(),
            "status": "oom" if is_oom(exc) else "error",
            "notes": f"ttft_proxy=batch_wall; vram_source=nvml; {type(exc).__name__}: {exc}",
        }

    if not outputs:
        return {
            "prompt_tokens": 0,
            "ttft_ms": None,
            "total_ms": None,
            "tokens_per_s": None,
            "peak_vram_mb": peak_vram_mb(),
            "status": "error",
            "notes": "ttft_proxy=batch_wall; vram_source=nvml; empty_outputs",
        }

    # Batch wall = time to serve N concurrent under CB (all admitted together).
    # Per-request tok/s uses that shared wall (Phase 1 median of per-request rates).
    rates = []
    for out in outputs:
        new_tokens = max(len(out.outputs[0].token_ids), 1)
        rates.append(new_tokens / (wall_ms / 1000.0))
    prompt_tokens = len(outputs[0].prompt_token_ids)

    return {
        "prompt_tokens": prompt_tokens,
        "ttft_ms": wall_ms,
        "total_ms": wall_ms,
        "tokens_per_s": statistics.median(rates),
        "peak_vram_mb": peak_vram_mb(),
        "status": "ok",
        "notes": "ttft_proxy=batch_wall; vram_source=nvml; batch_generate=1",
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
            "vLLM not installed. Pin is 0.26.0.\n"
            f"  Colab/Kaggle T4 (CUDA 12.x drivers):\n"
            f"    pip install {CU129_WHEEL}\n"
            "  Linux with CUDA 13 runtime:\n"
            "    pip install vllm==0.26.0\n"
            "  Do not use `uv sync --group gpu` — that group is empty "
            "(pin conflicts with this repo's cu124 torch index).",
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

    # Discard cold start / cudagraph capture from the timed sweep.
    print("warmup batch generate…", flush=True)
    try:
        run_concurrent(llm, f"{prompt} [warmup]", 1, 8)
    except Exception as exc:  # noqa: BLE001
        print(f"warmup failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

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
                    "notes": f"ttft_proxy=batch_wall; vram_source=nvml; {type(exc).__name__}: {exc}",
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
