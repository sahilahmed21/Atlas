# Phase 8 — before / after load gate

**Date:** 2026-08-12  
**worker_mode:** `simulated` (required AC-005; live optional — see guide)  
**Source:** `results/phase8/gate_matrix.csv`  
**Gate:** `ATLAS_PREFIX_LOAD_MARGIN` / `load_margin` — default **0** (off); Phase 8 cell uses **1**  
**Pressure signal:** in-flight loads + soft `served_counts` when margin > 0 (sequential free-path proxy; not llm-d EPP)

## Three-way high_reuse (n=24)

| Strategy | load_margin | TTFT p50 | TTFT p95 | hit% | hit_broken% | skew |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| round_robin | 0 | **147.5** | **281.25** | 0 | 0 | 0.5 |
| prefix_aware (sticky) | 0 | 297.5 | 556.25 | **95.83** | 0 | **1.0** |
| prefix_aware + gate | 1 | **147.5** | **281.25** | 45.83 | **50.0** | **0.5** |

## Verdict

On the Phase 5 soft-sat sim, the load gate **recovers RR-class TTFT** (p50 147.5) while still claiming some sticky hits (45.83%) and breaking half the affinity decisions (`hit_broken`). Skew returns to 0.5.

Heuristic gate ≠ production llm-d EPP. Live GPU before/after is optional confirmation (Phase 7 dual-vLLM recipe).

## Reproduce

```powershell
uv run python benchmarks/run_routing_matrix.py --phase8 --n 24
# live (optional):
uv run python benchmarks/run_routing_matrix.py --phase8 --worker-mode live --n 24 `
  --hardware colab-t4 --vllm-version 0.26.0 --replica-mode time_sliced_dual
```
