# Acceptance Brief: Phase 5.5 live dashboard

**Status:** Draft — implementing  
**Revision:** 1  
**Approval required before risky work:** No — offline/fake-worker demo path; inventing metrics forbidden

## Revision Log

| Rev | Date | Changed criteria | Reason |
| --- | --- | --- | --- |
| 1 | 2026-08-10 | AC-001–007 | Initial Phase 5.5 from architecture |

## Goal

Show a live per-request feed (replica, route reason, cache signal, TTFT/tokens/s) sourced from the same gateway request path as Prometheus — plus a minimal HTML dashboard — without inventing UI numbers.

## Scope

**In scope**
- Process-local `RequestEvent` ring buffer published beside `observe_request`
- `GET /atlas/snapshot` + `GET /atlas/events` (SSE) with tenant auth
- Static `dashboard/` UI at `/dashboard/` consuming snapshot+SSE
- Honesty labeling; no prompt/user text in events
- Demo runbook; video recording deferred (link empty)

**Out of scope**
- Grafana as primary UX, Postgres, React SPA, Colab requirement
- Recording the 90s video in-repo
- TTFT load gate / Phase 6 pitch

## Context

**Discovered facts**
- `/metrics` is aggregates only; headers carry per-request route fields but no live feed
- `observe_request` is the single request-path metrics write site (4 call sites in gateway)
- `dashboard/` is README-only; `jinja2` already in deps (plain HTML preferred)

**Assumptions**
- Query `api_key` on `/atlas/*` only is acceptable for EventSource (Bearer still works)
- Fake worker behind gateway is valid for live demo if labeled

## Acceptance Criteria

### AC-001: Event log stores request fields without prompt text
- **Scenario:** publish one event with route fields + timings
- **Expected:** snapshot contains id, worker_id, strategy, reason, cache_signal, ttft_ms, outcome; no message/prompt fields
- **Verification:** `uv run pytest platform/observability/test_request_events.py -q`
- **Priority:** Required

### AC-002: Ring buffer drops oldest when full
- **Scenario:** maxlen=3; publish 4 events
- **Expected:** snapshot has 3 newest ids
- **Verification:** unit test
- **Priority:** Required

### AC-003: Chat completion publishes an event
- **Scenario:** authenticated chat via gateway with fake worker
- **Expected:** `/atlas/snapshot` shows ≥1 event matching `x-atlas-worker-id` / cache_signal / strategy
- **Must not:** invent timings absent from observe path
- **Verification:** `uv run pytest platform/gateway/test_gateway_live_events.py -q`
- **Priority:** Required

### AC-004: Snapshot/events require auth
- **Scenario:** no key / wrong key
- **Expected:** 401; valid Bearer or `api_key` query succeeds
- **Verification:** gateway live-events tests
- **Priority:** Required

### AC-005: SSE streams new events after connect
- **Scenario:** client opens `/atlas/events`; then a chat completes
- **Expected:** SSE body contains a `data:` JSON event with worker_id
- **Verification:** gateway live-events tests
- **Priority:** Required

### AC-006: Dashboard HTML served with honesty banner
- **Scenario:** `GET /dashboard/` or `/dashboard/index.html`
- **Expected:** 200 HTML mentioning live metrics / process-local (or honesty phrasing)
- **Verification:** gateway or dashboard test
- **Priority:** Required

### AC-007: Demo docs updated; video deferred
- **Scenario:** phase close
- **Expected:** `DEMO.md` runbook steps runnable; video link still “Not recorded”; HANDOFF next=Phase 6
- **Verification:** doc review
- **Priority:** Required

## Verification Plan

| Criterion | Evidence | Status |
| --- | --- | --- |
| AC-001–002 | observability unit tests | Pending |
| AC-003–006 | gateway live + dashboard tests | Pending |
| AC-007 | DEMO + HANDOFF | Pending |
