# results/phase5-live/

**Phase 7 landing zone.**

| File | Role |
| --- | --- |
| `routing_matrix_live.csv` | GPU-backed matrix rows (`worker_mode=live`) |
| `SURPRISE_GPU.md` | Verdict vs Phase 5 sim — write after the Colab run |
| `README.md` | This file — reproduce notes |

## Reproduce (after dual vLLM is up)

```powershell
# From repo root, with workers on :8001 and :8002
uv run python benchmarks/run_routing_matrix.py --worker-mode live `
  --patterns high_reuse --strategies round_robin,prefix_aware --n 24 `
  --hardware colab-t4 --vllm-version 0.26.0 `
  --replica-mode time_sliced_dual
```

Label `replica_mode=sequential_isolated` if dual concurrent OOM forced sequential runs.

Until a real GPU CSV exists: cite only `results/phase5/` and label it `worker_mode=simulated`.
