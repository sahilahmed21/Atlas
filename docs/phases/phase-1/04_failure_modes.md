# Phase 1 — Failure modes → Phase 2 inputs

Each mode must cite Phase 1 evidence (math row or CSV row).

| ID | Failure mode | Evidence | Phase 2 toy that addresses it |
| --- | --- | --- | --- |
| F1 | Contiguous KV allocation wastes memory under variable seq lengths | | Naive vs paged allocator |
| F2 | Static batching leaves GPU idle between request arrivals | | Static vs continuous scheduler |
| F3 | Shared prompt prefixes recomputed every time | | Prefix-hash cache |
| F4 | _(optional)_ No preemption / unfair long requests | | Note only; may defer |

## Fundamentals check (must answer in one sentence each)

1. F1 is fixed by paging because: _
2. F2 is fixed by continuous batching because: _
3. F3 is fixed by prefix caching because: _
