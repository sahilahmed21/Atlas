# Acceptance Brief: Phase 7 live GPU routing validation

**Status:** **Done** (2026-08-12) — AC-001–006 pass; verdict **WEAKENED**  
**Revision:** 3  
**Approval required before risky work:** Yes — Colab GPU cost/time; inventing GPU numbers forbidden  
**Artifacts:** `results/phase5-live/routing_matrix_live.csv` · `SURPRISE_GPU.md`

## Goal

Produce a **GPU-backed** high_reuse comparison of round_robin vs prefix_aware through the real gateway, with artifacts under `results/phase5-live/`.

## Scope

**In scope**
- Dual (or sequential-isolated) vLLM OpenAI servers + Atlas gateway
- high_reuse × {round_robin, prefix_aware} at minimum
- CSV + `SURPRISE_GPU.md` with hardware/version/replica_mode labels
- Repro notes (README or notebook)

**Out of scope**
- Load gate implementation
- Claiming sim and GPU must match
- Multi-node / RDMA

## Risk Review

| Risk | Handling |
| --- | --- |
| Honesty | Label replica_mode; never invent TTFT; no empty charts |
| Cost | Prefer single surprise cell before full 3×4 matrix |
| Compatibility | Keep existing OpenAI path; no auth bypass |
| Security | Synthetic keys only; no prompt logging in events |

## Acceptance Criteria

### AC-001: Live workers behind gateway
- **Expected:** `workers.yaml` base_urls point at real OpenAI-compatible vLLM; chat completions succeed with `x-atlas-*` headers
- **Must not:** use `SimulatedWorkerClient` for Phase 7 evidence rows
- **Verification:** run log / notebook + `worker_mode=live` CSV rows
- **Priority:** Required
- **Result:** **PASS**

### AC-002: high_reuse × RR and prefix_aware measured
- **Expected:** both strategy rows in `routing_matrix_live.csv` with n≥ documented minimum (recommend n≥24 or justify)
- **Must not:** single anecdotal curl as the only evidence
- **Verification:** CSV exists and parses
- **Priority:** Required
- **Result:** **PASS** (n=24 both strategies)

### AC-003: SURPRISE_GPU.md verdict
- **Expected:** explicit compare to Phase 5 sim — confirm / weaken / refute — with hypothesis
- **Must not:** hide disagreement
- **Verification:** file review
- **Priority:** Required
- **Result:** **PASS** — verdict **WEAKENED**

### AC-004: Metadata on every claim
- **Expected:** hardware, vLLM version, model, replica_mode, date in README or SURPRISE_GPU
- **Verification:** file review
- **Priority:** Required
- **Result:** **PASS**

### AC-005: Claim inventory updated
- **Expected:** Phase 7 allowed/forbidden rows added to `docs/phases/phase-6/CLAIM_INVENTORY.md`
- **Verification:** inventory diff
- **Priority:** Required
- **Result:** **PASS**

### AC-006: No DistServe / APC overclaim
- **Expected:** write-up states router signal ≠ engine APC; no multi-node claim
- **Verification:** file review
- **Priority:** Required
- **Result:** **PASS**

## Done when

AC-001–006 pass. **Met.** Phase 8 may start.
