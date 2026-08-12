# Acceptance Brief: Phase 8 TTFT / load gate

**Status:** **Done** (sim required ACs) — live Colab gate matrix optional  
**Revision:** 2  
**Artifacts:** `results/phase8/gate_matrix.csv` · `BEFORE_AFTER.md`

## Goal

Ship a minimal prefix-aware **load gate** and prove with a three-way matrix that the gate improves the high_reuse loss case (or document why it does not).

## Acceptance Criteria

### AC-001: Sticky when cool — **PASS**
### AC-002: Break when hot — **PASS** (`cache_signal=hit_broken`)
### AC-003: Miss path unchanged — **PASS**
### AC-004: Gateway integration — **PASS** (`test_prefix_aware_load_gate_breaks_sticky_under_served_pressure`)
### AC-005: Before/after artifact — **PASS** (sim three-way)
### AC-006: Claim inventory — **PASS**
### AC-007: Default safe — **PASS** (`load_margin` default 0 / `ATLAS_PREFIX_LOAD_MARGIN=0`)

## Done when

AC-001–007 pass. **Met for sim.** Phase 9 may start. Optional: live `--phase8 --worker-mode live` on dual vLLM.
