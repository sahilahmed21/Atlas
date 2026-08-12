# Acceptance Brief: Phase 6 honest write-up + pitch

**Status:** Implemented  
**Revision:** 1  
**Approval required before risky work:** No — docs-only; inventing metrics forbidden

## Goal

Publish a defensible constraint → measured → future-work narrative. Every public number cites an artifact in `CLAIM_INVENTORY.md`.

## Scope

**In scope**
- Claim inventory + this acceptance brief
- Pitch paragraph + resume bullets
- Phase 6 README narrative arc; root README status + short arc
- HANDOFF / phase index closure

**Out of scope**
- Gateway/router/code changes, DB, DistServe, TTFT load gate, demo video recording, Colab re-run

## Acceptance criteria

| ID | Criterion | Evidence |
| --- | --- | --- |
| AC-001 | Claim inventory lists allowed / forbidden / future with paths | `CLAIM_INVENTORY.md` |
| AC-002 | Pitch is present-tense for shipped phases; every number is allowed | `docs/pitch/ONE_PARAGRAPH.md` |
| AC-003 | Resume bullets cite Phase 1 cliff + Phase 5 sim surprise + no DistServe-as-built | `docs/pitch/RESUME_BULLETS.md` |
| AC-004 | Phase 6 README arc covers constraint → naive → built → surprise → live → future | `README.md` (this dir) |
| AC-005 | Root README marks Phase 6 done; no empty demo video link | Root `README.md` |
| AC-006 | Phase index + HANDOFF show Phase 6 done | `docs/phases/README.md`, `docs/HANDOFF.md` |
| AC-007 | No claim that Phase 5 is GPU TTFT or that disaggregation is implemented | Manual read of pitch + resume + README arc |

## Done when

AC-001–007 pass by reading the listed files. No pytest required.
