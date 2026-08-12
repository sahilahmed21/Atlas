# benchmarks/

Load generators and comparison harnesses. Prefer scripts that read `configs/` and write `results/`.

## Phase 5 routing matrix (simulated)

```powershell
uv run python benchmarks/run_routing_matrix.py
uv run pytest benchmarks -q
```

Writes `results/phase5/routing_matrix.csv` (`worker_mode=simulated`).

## Phase 7 live GPU matrix

Requires two OpenAI-compatible vLLM servers (see `docs/phases/phase-7/START_HERE.md`).

```powershell
uv run python benchmarks/run_routing_matrix.py --worker-mode live `
  --patterns high_reuse --strategies round_robin,prefix_aware --n 24 `
  --hardware colab-t4 --vllm-version 0.26.0 --replica-mode time_sliced_dual `
  --worker-a-url http://127.0.0.1:8001/v1 --worker-b-url http://127.0.0.1:8002/v1
```

Writes `results/phase5-live/routing_matrix_live.csv` (`worker_mode=live`, streaming TTFT).
Do **not** cite live rows unless real vLLM was behind those URLs (tests use MockTransport only).
