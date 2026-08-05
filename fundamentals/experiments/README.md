# experiments/

Phase 1 (built):

- `naive_hf_load.py` — concurrency sweep → `results/phase1/naive_load.csv`
- `plot_failure_curve.py` — CSV → `results/phase1/oom_latency_curve.png`
- `test_plot_failure_curve.py` — guards latency-cliff / OOM classification

```powershell
uv run python fundamentals/experiments/naive_hf_load.py
uv run python fundamentals/experiments/plot_failure_curve.py
uv run pytest fundamentals/experiments
```

Protocol: `docs/phases/phase-1/02_naive_baseline.md`
