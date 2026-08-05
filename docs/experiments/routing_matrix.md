# Routing experiment matrix (Phase 5)

| Traffic \ Strategy | Round robin | Least load | Prefix-aware |
| --- | --- | --- | --- |
| High prefix reuse | Not run — Phase 5 blocked on platform/router | Not run — Phase 5 blocked on platform/router | Not run — Phase 5 blocked on platform/router |
| Low prefix reuse | Not run — Phase 5 blocked on platform/router | Not run — Phase 5 blocked on platform/router | Not run — Phase 5 blocked on platform/router |
| Bursty | Not run — Phase 5 blocked on platform/router | Not run — Phase 5 blocked on platform/router | Not run — Phase 5 blocked on platform/router |
| Steady | Not run — Phase 5 blocked on platform/router | Not run — Phase 5 blocked on platform/router | Not run — Phase 5 blocked on platform/router |

Cells: TTFT p50/p95, tokens/s, cache hit %, notes.

**Required:** highlight ≥1 cell where prefix-aware is worse; write hypothesis in `results/phase5/SURPRISE.md`.

No Phase 5 results exist yet. Preserve this matrix as a result table: replace each status with
TTFT p50/p95, tokens/s, cache hit %, run identifier, and a short interpretation only after all
strategies have run on the same traffic trace.
