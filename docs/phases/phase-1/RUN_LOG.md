# Phase 1 run log

| Date | Hardware | Model | Command / notebook | Result summary | Artifact |
| --- | --- | --- | --- | --- | --- |
| 2026-07-27 | laptop-3050 (4GB) | TinyLlama-1.1B fp16 | load attempt | **OOM / page-file fail at load** — weights ~2.05 GiB + allocator warmup exceed usable VRAM/RAM; abandoned for Phase 1 | — |
| 2026-07-27 | laptop-3050 (4GB) | Qwen2.5-0.5B-Instruct @ 7ae5576 | `uv run python fundamentals/experiments/naive_hf_load.py --n-only 1` | N=1 ok (~1.6s, ~969 MB peak) | `results/phase1/naive_load_dryrun.csv` |
| 2026-07-27 | laptop-3050 (4GB) | Qwen2.5-0.5B-Instruct @ 7ae5576 | `uv run python fundamentals/experiments/naive_hf_load.py` | Latency cliff at **N=8, max_new_tokens=32** (p50 9242 ms ≈ 5.5× N=1 1671 ms). No CUDA OOM. Peak VRAM only ~1.04 GB. | `results/phase1/naive_load.csv` |
| 2026-07-28 | laptop-3050 (4GB) | Qwen2.5-0.5B-Instruct @ 7ae5576 | `uv run pytest fundamentals/experiments` then `uv run python fundamentals/experiments/plot_failure_curve.py` | 4 tests pass (cliff/OOM classification); chart rendered from CSV | `results/phase1/oom_latency_curve.png`, `docs/testing/phase-1.tdd.md` |

## Notes

### Wrong / refined predictions
- Memory-math prediction of first OOM at `B=8, S=4096` was **not hit** in this sweep — VRAM stayed ~1 GB. Root cause of the miss: the sweep varied **concurrency only**, so `S` stayed ≈55 tokens and the KV term was never stressed. The prediction is untested, not disproven.
- `configs/models/phase1.yaml` lists 32 and 128 generated tokens, but only the 32-token leg ran:
  the harness stops the sweep after the documented N=8 latency cliff. The 128-token/sequence-length
  sweep is deferred rather than silently treated as completed.
- **Latency collapse before OOM: confirmed (Yes).** Failure mode is contention / serialization under naive threaded `generate()`, not KV bytes exceeding 4 GiB.
- **Weights term validated:** predicted 942 MiB vs 969.2 MiB measured at N=1 (3% gap).
- **Unpredicted finding:** N=1→N=8 grew peak VRAM by 73.7 MB where KV math predicts 4.5 MiB — ~16× allocation overhead. Became evidence for F1.
- TinyLlama-1.1B is too large for comfortable Phase 1 on this 3050; Qwen2.5-0.5B is the pinned laptop model.

### CUDA quirks
- HF Hub Python client hung on weight download (Xet); used `curl.exe` into `models/`.
- `device_map={"": 0}` triggered `caching_allocator_warmup` double-reserve OOM on TinyLlama; load-then-`.to(cuda)` used instead.
- Windows page file too small to materialize TinyLlama on CPU.
