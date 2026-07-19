# ADR 0002 — fundamentals vs platform split

**Status:** Accepted  
**Date:** 2026-07-19

## Decision

Keep educational / toy mechanisms under `fundamentals/` and production path under `platform/` + `workers/`. Do not merge into one package as the project scales.

## Consequences

- Clear MVP → final growth path  
- Phase 3 can diff toys against vLLM without deleting them  
- Interview demos can show both "I understand" and "I shipped"
