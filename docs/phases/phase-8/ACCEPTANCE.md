# Acceptance Brief: Phase 8 TTFT / load gate

**Status:** Not started  
**Revision:** 1  
**Approval required before risky work:** No for sim TDD; Yes for claiming live GPU recovery numbers

## Goal

Ship a minimal prefix-aware **load gate** and prove with a three-way matrix that the gate improves the high_reuse loss case (or document why it does not).

## Scope

**In scope**
- Break sticky hit when owner is sufficiently hotter than least-load alternate
- Reason string + test coverage
- `results/phase8/` before/after write-up
- Sim matrix required; live optional but preferred

**Out of scope**
- Full llm-d EPP / KV-event precise scoring
- Dashboard redesign
- Phase 9 recording

## Acceptance Criteria

### AC-001: Sticky when cool
- **Scenario:** owner exists; owner load ≤ alternate + margin
- **Expected:** hit → owner; `cache_signal=hit`
- **Verification:** router unit test
- **Priority:** Required

### AC-002: Break when hot
- **Scenario:** owner load ≥ alternate + margin
- **Expected:** routes to cooler worker; reason mentions gate/break; documented cache_signal semantics
- **Verification:** router unit test
- **Priority:** Required

### AC-003: Miss path unchanged
- **Scenario:** no owner
- **Expected:** still least_load claim + miss
- **Verification:** unit test
- **Priority:** Required

### AC-004: Gateway integration
- **Scenario:** prefix_aware + gate enabled under TestClient / sim workers
- **Expected:** headers/events show break reason under forced hot load
- **Verification:** gateway or harness test
- **Priority:** Required

### AC-005: Before/after artifact
- **Expected:** `results/phase8/BEFORE_AFTER.md` + CSV with RR, prefix, prefix+gate on high_reuse
- **Must not:** resume “improved X%” without these rows
- **Verification:** file review
- **Priority:** Required

### AC-006: Claim inventory
- **Expected:** new allowed claims + “heuristic gate ≠ llm-d EPP” forbidden overclaim
- **Verification:** inventory update
- **Priority:** Required

### AC-007: Default safe
- **Expected:** gate off or margin documented so Phase 5/7 repro of sticky loss still possible
- **Verification:** README + config default note
- **Priority:** Required

## Done when

AC-001–007 pass. Phase 9 may start.
