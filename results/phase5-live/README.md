# results/phase5-live/

**Phase 7 landing zone.**

| File | Role |
| --- | --- |
| `routing_matrix_live.csv` | GPU-backed matrix (`worker_mode=live`) — **not present yet** |
| `SURPRISE_GPU.md` | Verdict vs Phase 5 sim — after a valid live run |
| `README.md` | This file |

## Session 2026-08-12

- Dual vLLM on Colab T4 **worked** (8001+8002, util 0.4 each). See `docs/phases/phase-7/RUN_LOG.md`.
- Matrix cell ran on git tip **without** live harness → sim CSV under `results/phase5/` only.
- **Do not** treat those simulated TTFT/hit% rows as Phase 7 evidence.

## Reproduce (valid live run)

**Prerequisite:** tree ≥ `517a309` (`feat: Phase 7 live routing matrix harness`). Confirm:

```bash
uv run python benchmarks/run_routing_matrix.py --help | grep worker-mode
```

Then, with workers on :8001 and :8002:

```powershell
uv run python benchmarks/run_routing_matrix.py --worker-mode live `
  --patterns high_reuse --strategies round_robin,prefix_aware --n 24 `
  --hardware colab-t4 --vllm-version 0.26.0 `
  --replica-mode time_sliced_dual
```

Expect: `wrote .../results/phase5-live/routing_matrix_live.csv` and every row `worker_mode=live`.

Until that file exists: cite only `results/phase5/` as `worker_mode=simulated`.
