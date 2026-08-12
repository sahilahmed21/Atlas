# benchmarks/

Load generators and comparison harnesses. Prefer scripts that read `configs/` and write `results/`.

## Phase 5 routing matrix (simulated)

```powershell
uv run python benchmarks/run_routing_matrix.py
uv run pytest benchmarks -q
```

Writes `results/phase5/routing_matrix.csv` (`worker_mode=simulated`, `load_margin=0`).

## Phase 7 live GPU matrix

Requires two OpenAI-compatible vLLM servers (see `docs/phases/phase-7/START_HERE.md`).

```powershell
uv run python benchmarks/run_routing_matrix.py --worker-mode live `
  --patterns high_reuse --strategies round_robin,prefix_aware --n 24 `
  --hardware colab-t4 --vllm-version 0.26.0 --replica-mode time_sliced_dual `
  --worker-a-url http://127.0.0.1:8001/v1 --worker-b-url http://127.0.0.1:8002/v1
```

## Phase 8 load gate matrix

```powershell
uv run python benchmarks/run_routing_matrix.py --phase8 --n 24
# optional live:
uv run python benchmarks/run_routing_matrix.py --phase8 --worker-mode live --n 24
```

Writes `results/phase8/gate_matrix.csv`. Default gate off (`--load-margin 0`); `--phase8` uses margin 1 on the gated cell.
