# Phase 1 checklist

- [ ] Model chosen + pinned in `configs/models/phase1.yaml`
- [ ] Memory table filled (≥3 rows) in `01_memory_math.md`
- [ ] Predictions written *before* load sweep
- [ ] `fundamentals/experiments/naive_hf_load.py` exists and N=1 works
- [ ] `results/phase1/naive_load.csv` has multi-N rows including failure
- [ ] Curve plotted + captioned in `03_failure_curve.md`
- [ ] Failure modes F1–F3 filled in `04_failure_modes.md`
- [ ] Runs logged in `RUN_LOG.md`
- [ ] Phase 2 unblocked

**Done when:** someone else can reproduce the curve from docs + config alone.
