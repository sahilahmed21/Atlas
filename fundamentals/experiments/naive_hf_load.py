"""Phase 1 — naive HuggingFace concurrent generate() load sweep.

Reads configs/models/phase1.yaml, runs N concurrent generate() workers,
appends rows to results/phase1/naive_load.csv.

Protocol: docs/phases/phase-1/02_naive_baseline.md
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import torch
import yaml
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs" / "models" / "phase1.yaml"
DEFAULT_OUT = ROOT / "results" / "phase1" / "naive_load.csv"

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
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_dtype(name: str) -> torch.dtype:
    mapping = {
        "float16": torch.float16,
        "fp16": torch.float16,
        "bfloat16": torch.bfloat16,
        "bf16": torch.bfloat16,
        "float32": torch.float32,
        "fp32": torch.float32,
    }
    key = name.lower()
    if key not in mapping:
        raise ValueError(f"Unsupported dtype {name!r}; expected one of {sorted(mapping)}")
    return mapping[key]


def peak_vram_mb() -> float | None:
    if not torch.cuda.is_available():
        return None
    return torch.cuda.max_memory_allocated() / (1024**2)


def reset_peak_vram() -> None:
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()


def is_oom(exc: BaseException) -> bool:
    if isinstance(exc, torch.cuda.OutOfMemoryError):
        return True
    text = f"{type(exc).__name__}: {exc}".lower()
    return "out of memory" in text or "cuda out of memory" in text


def one_generate(
    model,
    tokenizer,
    prompt: str,
    max_new_tokens: int,
    device: torch.device,
) -> dict:
    """Run a single generate(); return timing metrics or raise."""
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    prompt_tokens = int(inputs["input_ids"].shape[-1])

    t0 = time.perf_counter()
    with torch.inference_mode():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            use_cache=True,
            pad_token_id=tokenizer.pad_token_id,
        )
    if device.type == "cuda":
        torch.cuda.synchronize()
    total_ms = (time.perf_counter() - t0) * 1000.0
    new_tokens = max(int(out.shape[-1]) - prompt_tokens, 1)
    return {
        "prompt_tokens": prompt_tokens,
        "total_ms": total_ms,
        "tokens_per_s": new_tokens / (total_ms / 1000.0),
        "new_tokens": new_tokens,
    }


def run_concurrent(
    model,
    tokenizer,
    prompt_template: str,
    n: int,
    max_new_tokens: int,
    device: torch.device,
) -> dict:
    """Launch N threaded generate() calls; aggregate p50 metrics."""
    reset_peak_vram()
    results: list[dict] = []
    errors: list[str] = []
    oom = False

    def worker(i: int) -> dict:
        prompt = f"{prompt_template} [req={i}]"
        return one_generate(model, tokenizer, prompt, max_new_tokens, device)

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(worker, i) for i in range(n)]
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001 — record all worker failures
                if is_oom(exc):
                    oom = True
                    errors.append("oom")
                else:
                    errors.append(f"{type(exc).__name__}: {exc}")

    vram = peak_vram_mb()
    if oom:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return {
            "status": "oom",
            "prompt_tokens": results[0]["prompt_tokens"] if results else None,
            "ttft_ms": None,
            "total_ms": None,
            "tokens_per_s": None,
            "peak_vram_mb": vram,
            "notes": "ttft_proxy=total; concurrent generate OOM",
        }

    if not results:
        return {
            "status": "error",
            "prompt_tokens": None,
            "ttft_ms": None,
            "total_ms": None,
            "tokens_per_s": None,
            "peak_vram_mb": vram,
            "notes": f"ttft_proxy=total; errors={errors[:3]}",
        }

    total_ms = statistics.median(r["total_ms"] for r in results)
    tps = statistics.median(r["tokens_per_s"] for r in results)
    prompt_tokens = results[0]["prompt_tokens"]
    notes = "ttft_proxy=total"
    status = "ok"
    if errors:
        status = "error"
        notes += f"; partial_errors={errors[:2]}"

    return {
        "status": status,
        "prompt_tokens": prompt_tokens,
        "ttft_ms": total_ms,  # naive generate has no true TTFT
        "total_ms": total_ms,
        "tokens_per_s": tps,
        "peak_vram_mb": vram,
        "notes": notes,
    }


def append_csv(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k) for k in CSV_FIELDS})


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Naive HF concurrent load sweep (Phase 1)")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument(
        "--n-only",
        type=int,
        default=None,
        help="If set, only run this concurrency (e.g. 1 for dry-run) and first max_new_tokens",
    )
    p.add_argument(
        "--skip-warmup",
        action="store_true",
        help="Skip warmup generate (not recommended)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config)

    model_id = cfg["model_id"]
    # Allow repo-relative local checkpoints (e.g. models/TinyLlama-...)
    local_candidate = (ROOT / model_id).resolve()
    if local_candidate.exists():
        model_id = str(local_candidate)
    revision = cfg.get("revision", "main")
    log_model = cfg.get("hub_model_id", model_id)
    dtype = resolve_dtype(cfg.get("dtype", "float16"))
    prompt_template = cfg["prompt_template"]
    hardware = cfg.get("hardware_label", "unknown")
    cliff_factor = float(cfg.get("cliff_factor", 5.0))

    max_new_tokens_sweep = list(cfg.get("max_new_tokens_sweep", [32]))
    concurrency_sweep = list(cfg.get("concurrency_sweep", [1, 2, 4, 8]))

    if args.n_only is not None:
        concurrency_sweep = [args.n_only]
        max_new_tokens_sweep = max_new_tokens_sweep[:1]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device} model={log_model} path={model_id} rev={revision[:12]} dtype={dtype}", flush=True)

    tok_kwargs = {}
    model_kwargs = {
        "dtype": dtype,
        "low_cpu_mem_usage": True,
    }
    local_model = Path(model_id).exists()
    if not local_model:
        tok_kwargs["revision"] = revision
        model_kwargs["revision"] = revision

    tokenizer = AutoTokenizer.from_pretrained(model_id, **tok_kwargs)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Avoid device_map={"":0} — transformers' caching_allocator_warmup can
    # reserve ~weights GiB *before* load and OOM a 4GB card. Load then .to().
    model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
    model.to(device)
    model.eval()

    if not args.skip_warmup:
        print("warmup generate…", flush=True)
        try:
            one_generate(model, tokenizer, f"{prompt_template} [warmup]", 8, device)
        except Exception as exc:  # noqa: BLE001
            print(f"warmup failed: {exc}", file=sys.stderr)
            if is_oom(exc):
                print("OOM at warmup/N≈1 — switch to smaller model in phase1.yaml", file=sys.stderr)
                return 2
            traceback.print_exc()
            return 1
        reset_peak_vram()

    baseline_n1_ms: dict[int, float] = {}
    stop_sweep = False

    for max_new_tokens in max_new_tokens_sweep:
        if stop_sweep:
            break
        for n in concurrency_sweep:
            print(f"run n={n} max_new_tokens={max_new_tokens} …", flush=True)
            metrics = run_concurrent(
                model, tokenizer, prompt_template, n, max_new_tokens, device
            )
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

            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            row = {
                "timestamp": ts,
                "hardware": hardware,
                "model": log_model,
                "n_concurrent": n,
                "prompt_tokens": metrics["prompt_tokens"],
                "max_new_tokens": max_new_tokens,
                "ttft_ms": (
                    f"{metrics['ttft_ms']:.3f}" if metrics["ttft_ms"] is not None else ""
                ),
                "total_ms": (
                    f"{metrics['total_ms']:.3f}" if metrics["total_ms"] is not None else ""
                ),
                "tokens_per_s": (
                    f"{metrics['tokens_per_s']:.3f}"
                    if metrics["tokens_per_s"] is not None
                    else ""
                ),
                "peak_vram_mb": (
                    f"{metrics['peak_vram_mb']:.1f}"
                    if metrics["peak_vram_mb"] is not None
                    else ""
                ),
                "status": metrics["status"],
                "notes": notes,
            }
            append_csv(args.out, row)
            print(
                f"  status={row['status']} total_ms={row['total_ms']} "
                f"peak_vram_mb={row['peak_vram_mb']}",
                flush=True,
            )

            if metrics["status"] == "oom":
                print("stopping sweep: OOM", flush=True)
                stop_sweep = True
                break

            if hit_cliff:
                print(
                    f"stopping sweep: latency cliff "
                    f"({metrics['total_ms']:.1f} ms > {cliff_factor}× {baseline:.1f} ms)",
                    flush=True,
                )
                stop_sweep = True
                break

    print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
