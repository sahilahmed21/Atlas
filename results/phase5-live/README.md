# results/phase5-live/

**Phase 7 landing zone — live high_reuse cell complete (2026-08-12).**

| File | Role |
| --- | --- |
| `routing_matrix_live.csv` | GPU-backed rows (`worker_mode=live`) |
| `SURPRISE_GPU.md` | Verdict vs Phase 5 sim: **WEAKENED** |
| `README.md` | Reproduce notes |

## Metadata (this run)

| Field | Value |
| --- | --- |
| Date | 2026-08-12 |
| Hardware | Colab Tesla T4 |
| vLLM | 0.26.0 |
| Model | `Qwen/Qwen2.5-0.5B-Instruct` |
| replica_mode | `time_sliced_dual` (util ≈0.4 / port) |
| Cells | high_reuse × {round_robin, prefix_aware}, n=24 |

## Headline (cite `SURPRISE_GPU.md`)

| Strategy | TTFT p50 | TTFT p95 | hit% | skew |
| --- | ---: | ---: | ---: | ---: |
| round_robin | 28.557 ms | 36.400 ms | 0 | 0.5 |
| prefix_aware | 33.320 ms | 44.787 ms | 95.83 | 1.0 |

Live sticky penalty ~1.17× p50 (sim claimed ~2×). Router hit behavior matches sim.

## Reproduce

```bash
# tip >= 517a309; dual vLLM on :8001/:8002
uv run python benchmarks/run_routing_matrix.py --help | grep worker-mode

uv run python benchmarks/run_routing_matrix.py --worker-mode live \
  --patterns high_reuse --strategies round_robin,prefix_aware --n 24 \
  --hardware colab-t4 --vllm-version 0.26.0 \
  --replica-mode time_sliced_dual \
  --worker-a-url http://127.0.0.1:8001/v1 \
  --worker-b-url http://127.0.0.1:8002/v1
```

Expect `worker_mode=live` in every CSV row. Phase 5 sim remains under `results/phase5/` only.
