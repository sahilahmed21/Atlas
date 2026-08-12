# Phase 8 — TTFT / load gate on prefix-aware

**Status:** **Done** (sim matrix + gate code) — live confirm optional  
**Depends on:** Phase 7 done; sim RED/GREEN sufficient for close  
**Eye-stopper:** `results/phase8/BEFORE_AFTER.md` — RR vs sticky vs **gated**  
**ACs:** [ACCEPTANCE.md](ACCEPTANCE.md)

## Goal

Close the Phase 5/7 sticky saturation loop with a minimal **load / TTFT gate**.

## Design (shipped)

- `PrefixAwareRouter(load_margin=N)` — break sticky when `owner_load >= alt_load + margin`
- `cache_signal=hit_broken`; reason includes `load_gate`
- Gateway: `ATLAS_PREFIX_LOAD_MARGIN` (default **0** = off). When >0, routing pressure = in-flight + soft `served_counts`
- Default off preserves Phase 5/7 sticky repro

## Config

```powershell
$env:ATLAS_PREFIX_LOAD_MARGIN = "1"   # enable gate
$env:ATLAS_STRATEGY = "prefix_aware"
```

## Artifacts

| Path | Contents |
| --- | --- |
| `platform/router/strategies.py` | Gate |
| `results/phase8/gate_matrix.csv` | Three-way sim |
| `results/phase8/BEFORE_AFTER.md` | Write-up |

## Reproduce

```powershell
uv run python benchmarks/run_routing_matrix.py --phase8 --n 24
```

## Honesty

Heuristic ≠ llm-d EPP. Sim used soft served pressure so sequential replay can exercise the gate.
