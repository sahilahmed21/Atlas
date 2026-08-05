# Phase 1 checklist

- [x] Model chosen + pinned in `configs/models/phase1.yaml`
- [x] Memory table filled (≥3 rows) in `01_memory_math.md`
- [x] Predictions written *before* load sweep
- [x] `fundamentals/experiments/naive_hf_load.py` exists and N=1 works
- [x] `results/phase1/naive_load.csv` has multi-N rows including failure
- [x] Curve plotted + captioned in `03_failure_curve.md`
- [x] Failure modes F1–F3 filled in `04_failure_modes.md`
- [x] Runs logged in `RUN_LOG.md`
- [x] Phase 2 unblocked

**Done when:** someone else can reproduce the curve from docs + config alone.

## Reproduce from scratch

```powershell
uv sync
# weights: models/ is gitignored; see RUN_LOG for the curl fetch (HF python client hangs on this host)
uv run python fundamentals/experiments/naive_hf_load.py      # -> results/phase1/naive_load.csv
uv run python fundamentals/experiments/plot_failure_curve.py # -> results/phase1/oom_latency_curve.png
uv run pytest fundamentals/experiments                       # guards the cliff/OOM classification
```

## Acceptance criteria status (`START_HERE.md`)

| AC | Requirement | Status |
| --- | --- | --- |
| AC-001 | Memory formula documented with own dims | Pass — `01_memory_math.md`, weights term validated within 3% of measured |
| AC-002 | Naive concurrent baseline with recorded failure | Pass — `naive_load.csv`, latency cliff at N=8 (5.5× N=1). No CUDA OOM; documented, not hidden |
| AC-003 | Eye-stopper chart from own data | Pass — `results/phase1/oom_latency_curve.png` |
| AC-004 | ≥3 failure modes named for Phase 2 | Pass — F1–F3 in `04_failure_modes.md`, each citing a CSV row |

**Caveat carried into Phase 2:** the sweep varied concurrency, not sequence length, so the KV term
of the memory math is validated only at `S≈55`. See "Known gap" in `03_failure_curve.md`.
