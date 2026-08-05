# TDD evidence — Phase 2 CPU toys

**Source plan:** [`docs/phases/phase-2/PLAN.md`](../phases/phase-2/PLAN.md)  
**Acceptance:** [`docs/phases/phase-2/ACCEPTANCE.md`](../phases/phase-2/ACCEPTANCE.md)

## User journeys

1. As an engineer reproducing Phase 2, I want contiguous vs paged waste on one fixed trace so F1 is measurable without a GPU.
2. As an engineer, I want static vs continuous busy fraction on one arrival trace so F2 is comparable within the sim model.
3. As an engineer, I want shared-prefix hits and unique-prefix zero hits so F3 prefill reuse is countable.

## Task report

### Task: Allocator (AC-001)

- **Summary:** Contiguous reserves `max_len`; paged reserves `ceil(used/16)*16`; CSV under `results/phase2/allocator.csv`.
- **RED:** `uv run pytest fundamentals/allocators -q` → `ModuleNotFoundError: No module named 'sim'`
- **GREEN:** `uv run pytest fundamentals/allocators -q` → `3 passed`
- **Guaranteed:** Contiguous waste uses max−used; paged waste ≤ one block; paged total waste < contiguous on `DEFAULT_TRACE`.

### Task: Scheduler (AC-002)

- **Summary:** Static waits for batch/timeout; continuous admits each step; CSV `scheduler.csv`.
- **RED:** `ModuleNotFoundError: No module named 'sim'`
- **GREEN:** `2 passed`; continuous busy_fraction 0.5417 ≥ static 0.3846
- **Guaranteed:** All requests complete; continuous busy fraction ≥ static on `DEFAULT_TRACE`; params recorded.

### Task: Prefix cache (AC-003)

- **Summary:** SHA-256 of token-id prefixes; shared vs unique traffic; CSV `prefix_cache.csv`.
- **RED:** `ModuleNotFoundError: No module named 'sim'`
- **GREEN:** `2 passed`; shared 7 hits / unique 0 hits
- **Guaranteed:** Shared traffic avoids `7×23` prefix tokens; unique traffic avoids 0.

## Test specification

| # | What is guaranteed | Test | Type | Result | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Contiguous reserves max_len and wastes unused tail | `test_contiguous_reserves_max_len_and_wastes_unused_tail` | unit | PASS | `uv run pytest fundamentals/allocators` |
| 2 | Paged waste bounded by one block | `test_paged_allocates_ceil_used_over_block_and_bounds_tail_waste` | unit | PASS | same |
| 3 | Paged total waste < contiguous | `test_paged_total_waste_is_less_than_contiguous_on_default_trace` | unit | PASS | same |
| 4 | Both schedulers complete all requests | `test_static_and_continuous_complete_all_requests` | unit | PASS | `uv run pytest fundamentals/schedulers` |
| 5 | Continuous busy ≥ static | `test_continuous_busy_fraction_at_least_static_on_default_trace` | unit | PASS | same |
| 6 | Shared prefix → 7 hits after first miss | `test_shared_prefix_traffic_gets_hits_after_first_miss` | unit | PASS | `uv run pytest fundamentals/prefix_cache` |
| 7 | Unique prefixes → 0 hits | `test_unique_prefix_traffic_has_zero_hits` | unit | PASS | same |

## Coverage and known gaps

No coverage tool configured. Deliberately untested: CSV writer formatting, CLI `main()`, external fragmentation across a shared memory pool (contiguous model is per-request reserve only), cache eviction.

## Merge evidence / checkpoints

| Commit message | Stage |
| --- | --- |
| `test: add Phase 2 allocator sim reproducers (RED)` | RED |
| `feat: Phase 2 contiguous vs paged allocator sim (GREEN)` | GREEN |
| `test: add Phase 2 scheduler sim reproducers (RED)` | RED |
| `feat: Phase 2 static vs continuous scheduler sim (GREEN)` | GREEN |
| `test: add Phase 2 prefix-cache sim reproducers (RED)` | RED |
| `feat: Phase 2 prefix-cache sim + Phase 2 close-out (GREEN)` | GREEN + AC-004 |

Modules were renamed to unique basenames (`*_sim.py` / `test_*_sim.py`) so
`pytest fundamentals/...` can collect all three toys in one invocation.
