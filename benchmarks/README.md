# benchmarks/

Load generators and comparison harnesses. Prefer scripts that read `configs/` and write `results/`.

## Phase 5 routing matrix

```powershell
uv run python benchmarks/run_routing_matrix.py
uv run pytest benchmarks -q
```

Writes `results/phase5/routing_matrix.csv` (`worker_mode=simulated`).
