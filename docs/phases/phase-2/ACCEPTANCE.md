# Acceptance Brief: Phase 2 CPU toys

**Status:** Approved for implementation  
**Revision:** 1  
**Source plan:** [`PLAN.md`](PLAN.md)  
**Approval required before risky work:** No — CPU sims only, no secrets/GPU/external paid calls

## Goal

Three deterministic CPU simulations isolate Phase 1 failure modes F1–F3 and write reproducible metrics under `results/phase2/`.

## Scope

**In scope**
- Contiguous vs paged allocator on one variable-S trace
- Static vs continuous scheduler on one arrival trace
- Token-id prefix cache on shared-prefix and unique-prefix traffic
- One small pytest suite per toy; fill measured sections in `01_`/`02_`/`03_`

**Out of scope**
- GPU, vLLM, platform gateway, eviction policy, F4 preemption
- Matching Phase 1 VRAM (+73.7 MB) or tok/s (27.7) numerically

## Assumptions

- `bytes_per_token = 12288` (Phase 1 Qwen math); `block_size = 16` tokens
- Scheduler capacity = 4; static batch size = 4; static timeout = 5 ticks
- Prefix cache keys whole shared prefix (document simplification vs block-aligned APC)
- Test runner: `uv run pytest`

## Acceptance Criteria

### AC-001: Paged waste below contiguous on fixed trace
- **Scenario:** Fixed request list with `max_len > used` for several requests
- **Action:** Run both allocators on that trace
- **Expected:** Sum of paged waste bytes < sum of contiguous waste bytes; CSV written
- **Must not:** Claim this explains Phase 1 GPU peak VRAM
- **Verification:** `uv run pytest fundamentals/allocators`
- **Priority:** Required

### AC-002: Continuous busy fraction ≥ static on fixed arrivals
- **Scenario:** Staggered arrivals with capacity and batch/timeout configured
- **Action:** Run both schedulers on the same trace
- **Expected:** Continuous `busy_fraction >=` static; seed/params recorded
- **Must not:** Equate sim work units to Phase 1 tok/s
- **Verification:** `uv run pytest fundamentals/schedulers`
- **Priority:** Required

### AC-003: Shared prefix hits; unique prefixes do not
- **Scenario:** Eight prompts with shared 23-token prefix + unique suffixes; eight unique prefixes
- **Action:** Run prefix cache on both traffic patterns
- **Expected:** Shared: ≥7 hits after first miss; Unique: 0 hits / 0 avoided prefill
- **Must not:** Claim decode latency improvement
- **Verification:** `uv run pytest fundamentals/prefix_cache`
- **Priority:** Required

### AC-004: Docs record simulated results
- **Scenario:** Sims produce CSVs
- **Action:** Fill measured sections; tick Phase 2 README checkboxes
- **Expected:** `01_`/`02_`/`03_` show numbers + sim-vs-measured disclaimer; checkboxes done
- **Verification:** Manual doc review
- **Priority:** Required

## Blocking Decisions

- None
