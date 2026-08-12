# Phase 8 — before / after load gate

**Date:** 2026-08-12 / 2026-08-13  
**Gate:** `ATLAS_PREFIX_LOAD_MARGIN` / `load_margin` — default **0** (off); gated cell uses **1**  
**Pressure signal:** in-flight + soft `served_counts` when margin > 0 (sequential free-path proxy; **≠** llm-d EPP)

## Sim three-way (required) — `gate_matrix.csv`

| Strategy | load_margin | TTFT p50 | TTFT p95 | hit% | hit_broken% | skew |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| round_robin | 0 | **147.5** | **281.25** | 0 | 0 | 0.5 |
| prefix_aware (sticky) | 0 | 297.5 | 556.25 | **95.83** | 0 | **1.0** |
| prefix_aware + gate | 1 | **147.5** | **281.25** | 45.83 | **50.0** | **0.5** |

**Sim verdict:** gate **recovers** sticky TTFT to RR-class on the soft-sat model.

## Live three-way (optional confirm) — `gate_matrix_live.csv`

**hardware:** Colab T4 · **vLLM:** 0.26.0 · **replica_mode:** time_sliced_dual · **n:** 24 · streaming TTFT

| Strategy | load_margin | TTFT p50 | TTFT p95 | hit% | hit_broken% | skew |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| round_robin | 0 | 35.857 | 44.626 | 0 | 0 | 0.5 |
| prefix_aware (sticky) | 0 | **26.441** | **32.300** | **95.83** | 0 | **1.0** |
| prefix_aware + gate | 1 | 33.174 | 49.017 | 45.83 | **50.0** | **0.5** |

**Live verdict: MECHANICS CONFIRMED, TTFT BENEFIT NOT CONFIRMED on this run.**

- Gate still fires as designed: `hit_broken` **50%**, skew **1.0 → 0.5** (same shape as sim).
- On this T4 dual-vLLM run, **sticky was fastest**; gated is ~**1.25×** sticky p50 and between sticky and RR.
- Differs from Phase 7 live cell (sticky ~1.17× worse than RR) — run variance / warming on time-sliced T4; do not force one narrative.
- Absolute ms are not comparable to sim soft-sat numbers.

## Honesty

- Heuristic gate ≠ llm-d EPP / real engine TTFT predictor.
- OTEL `Failed to detach context` noise under TestClient+stream is a known annoyance; CSV still wrote successfully.
- Router `cache_signal` ≠ vLLM APC.

## Reproduce

```powershell
uv run python benchmarks/run_routing_matrix.py --phase8 --n 24
uv run python benchmarks/run_routing_matrix.py --phase8 --worker-mode live --n 24 `
  --hardware colab-t4 --vllm-version 0.26.0 --replica-mode time_sliced_dual `
  --out results/phase8/gate_matrix_live.csv
```
