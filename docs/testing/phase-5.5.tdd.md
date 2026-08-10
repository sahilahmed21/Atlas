# TDD evidence — Phase 5.5 live dashboard

**Source plan:** Phase 5.5 architecture (chat-finalized)  
**Acceptance:** [`docs/phases/phase-5.5/ACCEPTANCE.md`](../phases/phase-5.5/ACCEPTANCE.md) (rev 1)

## User journeys

1. As a demo operator, I want each chat completion to emit a live event (worker, reason, cache, TTFT) from the same observe path as Prometheus.
2. As a viewer, I want `/dashboard/` to show a live clock and event feed without invented numbers.
3. As a security-conscious operator, I want `/atlas/*` authenticated (Bearer or query api_key for EventSource).

## Task report

### Task: RED

- **Command:** `uv run pytest platform/observability/test_request_events.py platform/gateway/test_gateway_live_events.py -q --tb=line`
- **Result:** `6 failed` — missing `request_events`, `/atlas/*`, dashboard mount
- **Checkpoint:** `d2d01e4` `test: Phase 5.5 live event feed + dashboard reproducers (RED)`

### Task: GREEN

- **Command:** `uv run pytest platform workers benchmarks -q`
- **Result:** `52 passed`
- **Guaranteed:** ring buffer; chat publishes events; snapshot/SSE auth; catch-up SSE; dashboard honesty HTML

## Test specification

| # | Guarantee | Test | Result |
| --- | --- | --- | --- |
| 1 | Event fields, no prompt text | `test_publish_snapshot_has_route_fields_not_prompt` | PASS |
| 2 | Ring drops oldest | `test_ring_drops_oldest_when_full` | PASS |
| 3 | Chat → snapshot event | `test_chat_publishes_live_event` | PASS |
| 4 | Auth on snapshot | `test_atlas_snapshot_requires_auth` | PASS |
| 5 | SSE catch-up emits worker_id | `test_atlas_events_sse_emits_after_chat` | PASS |
| 6 | Dashboard HTML honesty | `test_dashboard_html_served` | PASS |

Evidence: `uv run pytest platform workers benchmarks -q` → `52 passed`.

## Coverage and known gaps

No coverage % tool. Deferred: 90s demo video recording; Grafana primary UX; multi-replica event bus.

## Merge evidence / checkpoints

| Commit | Stage |
| --- | --- |
| `d2d01e4` test: Phase 5.5 … (RED) | RED |
| `ea84aa0` feat: Phase 5.5 live events + dashboard | GREEN |
