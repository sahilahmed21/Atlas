# Acceptance Brief: Phase 9 shock package

**Status:** Not started  
**Revision:** 1  
**Approval required before risky work:** No — publishing; inventing metrics still forbidden

## Goal

Ship a verifiable public package: demo video, README sell block, narrative post draft/publish, resume/pitch refresh.

## Scope

**In scope**
- 90s recording with checklist from phase-5.5 DEMO
- README top: table + demo link + reproduce
- `docs/pitch/PUBLIC_POST.md` (or published URL noted there)
- Pitch + resume bullets updated from inventory
- HANDOFF + claim inventory reflect Phase 9

**Out of scope**
- New experiments
- DistServe claims
- Phase 10

## Acceptance Criteria

### AC-001: Video exists and is linked
- **Expected:** non-empty URL in `phase-5.5/DEMO.md` and root README
- **Must not:** placeholder “TODO” link
- **Verification:** open URL
- **Priority:** Required

### AC-002: Demo checklist complete
- **Expected:** honesty banner, live metrics, comparison beat, honest limit — per DEMO.md
- **Verification:** watch once against checklist
- **Priority:** Required

### AC-003: README 30-second sell
- **Expected:** surprise table uses Phase 7 (and 8 if done) numbers only
- **Verification:** each number → inventory row
- **Priority:** Required

### AC-004: Public post
- **Expected:** `docs/pitch/PUBLIC_POST.md` complete; if published, URL recorded at top
- **Verification:** file review
- **Priority:** Required

### AC-005: Pitch / resume refreshed
- **Expected:** no future-tense for shipped 7–9 claims; no DistServe-as-built
- **Verification:** diff vs `CLAIM_INVENTORY.md`
- **Priority:** Required

### AC-006: Keys redacted
- **Expected:** video/README use demo key name only; no real secrets
- **Verification:** manual check
- **Priority:** Required

## Done when

AC-001–006 pass. Atlas is hire-signal packaged. Phase 10 optional only.
