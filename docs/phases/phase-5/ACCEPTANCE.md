# Acceptance Brief: Phase 5 routing experiment

**Status:** Implemented (offline simulated) — AC-001–008 evidenced  
**Revision:** 1  
**Approval required before risky work:** No — offline/simulated workers only; inventing GPU TTFT/cache forbidden

## Revision Log

| Rev | Date | Changed criteria | Reason |
| --- | --- | --- | --- |
| 1 | 2026-08-10 | AC-001–008 | Initial Phase 5 brief from architecture plan |

## Goal

Close the gateway routing control loop so prefix-aware and least-load are meaningful, then run a same-trace offline experiment that fills the strategy×traffic matrix and documents ≥1 cell where naive prefix-aware **loses**, with an honest hypothesis.

## Scope

**In scope**
- Shared prefix key (first system message, else first message) — labeled not vLLM block APC
- Process-local `prefix_owners` claim on miss + `loads` ±1 around upstream
- Prefix-aware miss placement via least-load (not lexicographic sticky)
- Offline matrix harness: fake workers with hit/miss + queue latency model; `worker_mode=simulated`
- Artifacts: `results/phase5/*.csv`, `SURPRISE.md`, filled `docs/experiments/routing_matrix.md`

**Out of scope**
- Live Colab dual-vLLM / real APC metrics
- TTFT load gate (llm-d `maxTTFTPenaltyMs`) — document as follow-up after loss is measured
- DB/Redis, strategies.yaml wiring, Phase 5.5 dashboard
- Random/sticky routers

## Context

**Discovered facts**
- Gateway injects `loads` / `prefix_owners` but never writes them after route
- `PrefixAwareRouter` hashes full prompt; miss → `sorted(workers)[0]`
- `benchmarks/` is README-only; matrix cells still “Not run”
- Phase 4 offline fake-worker evidence pattern is the precedent

**Assumptions**
- Simulated latency model is valid Phase 5 evidence if labeled `worker_mode=simulated`
- High-reuse sticky hot-spot (queue penalty > hit savings) is the primary surprise cell

## Risk Review

| Risk area | Applies? | Required handling |
| --- | --- | --- |
| Security/privacy | No new endpoints | Keep bearer auth; synthetic keys only |
| Persistent data/migration | No | Process-local dicts only |
| External effects/cost | No | Offline ASGI + fake workers |
| Compatibility/API | Yes | Preserve `/v1/chat/completions` + `x-atlas-*` headers |
| Honesty | Yes | Never claim GPU TTFT; label simulated |

## Acceptance Criteria

### AC-001: Shared prefix key ignores unique suffix
- **Scenario:** two chats share the same system message; user content differs
- **Action:** compute `shared_prefix_key(messages)` for both
- **Expected:** keys are equal
- **Must not:** hash the full concatenated prompt (which would diverge)
- **Verification:** `uv run pytest platform/router/test_router_strategies.py -q`
- **Priority:** Required

### AC-002: Prefix miss claims via least-load
- **Scenario:** empty owners; `loads` makes worker-b lighter than worker-a
- **Action:** `PrefixAwareRouter.choose(...)`
- **Expected:** miss → `worker-b`, `cache_signal=miss`
- **Must not:** always pick lexicographically first worker
- **Verification:** router unit test
- **Priority:** Required

### AC-003: Gateway writes owner on miss and hits on reuse
- **Scenario:** prefix_aware strategy; shared system + unique users; empty owners
- **Action:** two sequential chat completions with same system prefix
- **Expected:** first `x-atlas-cache-signal: miss`; second `hit`; both same `x-atlas-worker-id`; `app.state.prefix_owners` contains the key
- **Must not:** leave owners empty after first miss
- **Verification:** `uv run pytest platform/gateway/test_gateway_routing_state.py -q`
- **Priority:** Required

### AC-004: Gateway tracks in-flight loads
- **Scenario:** least_load strategy; two workers
- **Action:** complete one request; observe loads after completion; during an in-flight stream, load for that worker is ≥1
- **Expected:** after completion load returns to 0; least_load observes non-zero loads when injected mid-flight (or stream in-flight check)
- **Must not:** leave load permanently incremented after success
- **Verification:** gateway routing-state tests
- **Priority:** Required

### AC-005: Stream path decrements load
- **Scenario:** `stream=true` prefix_aware or least_load request completes
- **Action:** stream to `[DONE]`
- **Expected:** `app.state.loads[worker_id] == 0` after stream ends
- **Must not:** leak in-flight count on SSE path
- **Verification:** gateway routing-state stream test
- **Priority:** Required

### AC-006: Fake worker hit TTFT < miss TTFT; load adds penalty
- **Scenario:** simulated worker with known base_hit / base_miss / queue_penalty
- **Action:** chat with hit vs miss; miss under elevated load
- **Expected:** hit `ttft_ms` < miss `ttft_ms`; higher load → higher `ttft_ms`
- **Must not:** invent metrics outside the worker timing path
- **Verification:** `uv run pytest benchmarks/test_routing_matrix_harness.py -q`
- **Priority:** Required

### AC-007: Matrix runner writes same-trace CSV for 3 strategies × patterns
- **Scenario:** offline harness over frozen traces
- **Action:** run matrix for high_reuse, low_reuse, bursty, steady × round_robin, least_load, prefix_aware
- **Expected:** `results/phase5/routing_matrix.csv` rows with ttft p50/p95, cache hit %, worker skew, `worker_mode=simulated`
- **Must not:** mix strategies on different request sequences for a given pattern
- **Verification:** harness test + runner invocation
- **Priority:** Required

### AC-008: Document where prefix-aware loses
- **Scenario:** matrix complete
- **Action:** identify ≥1 cell where prefix-aware is worse on latency or fairness/skew vs RR or least_load
- **Expected:** `results/phase5/SURPRISE.md` hypothesis + filled `docs/experiments/routing_matrix.md`
- **Must not:** claim GPU truth or “prefix-aware always wins”
- **Verification:** artifacts exist; TDD evidence cites them
- **Priority:** Required

## Blocking Decisions

- [x] Evidence bar = offline simulated workers (locked in architecture plan)

## Verification Plan

| Criterion | Verification evidence | Status |
| --- | --- | --- |
| AC-001–002 | router pytest | PASS |
| AC-003–005 | gateway routing-state pytest | PASS |
| AC-006–007 | benchmarks harness pytest + runner | PASS |
| AC-008 | SURPRISE.md + matrix doc | PASS |
