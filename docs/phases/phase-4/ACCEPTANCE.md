# Acceptance Brief: Phase 4 platform end-to-end

**Status:** Implemented (E2E offline) — AC-001–013 evidenced with fake worker / httpx mocks  
**Revision:** 2  
**Approval required before risky work:** No — offline/fake-worker only; inventing live GPU metrics forbidden

## Revision Log

| Rev | Date | Changed criteria | Reason |
| --- | --- | --- | --- |
| 1 | 2026-08-07 | AC-001–007 | Scaffold |
| 2 | 2026-08-08 | AC-008–013 | Remaining Phase 4 E2E |

## Goal

Complete Phase 4 so the request path authenticates, rate-limits (honestly labeled), routes, talks to an OpenAI-compatible worker (stream timings preserved), and exports Prometheus metrics from that same path — with a KEDA sketch only as planning material.

## Scope

**In scope**
- Process-local RPM limiter labeled as not production-safe; HTTP 429 when exceeded
- Worker client streaming SSE + `ttft_ms` / `completion_ms` / `request_id` / outcome
- Gateway passthrough of upstream SSE when `stream=true`
- Prometheus metrics on the request path + `GET /metrics` (no synthetic dashboard events)
- Thin OTEL span hook around chat completions
- Queue-depth gauge + KEDA ScaledObject YAML sketch under `deploy/`
- Pin helper matching Phase 3 `0.26.0` when a worker reports a version

**Out of scope**
- Live Colab/GPU vLLM process in CI
- Distributed/shared RPM store
- Claiming KEDA was run in a cluster
- Invented TTFT/cache numbers not produced by the request path

## Context

**Discovered facts**
- Scaffold AC-001–007 green (`20 passed`)
- `prometheus-client` already in `pyproject.toml`; prefer `generate_latest` over `mount("/metrics")` to avoid trailing-slash redirect
- vLLM OpenAI stream = SSE `data: {json}` … `data: [DONE]`
- Exa MCP not configured in this environment; verified via web search instead

**Assumptions**
- Fake worker / httpx MockTransport is sufficient evidence for AC-008–013
- Process-local RPM + queue depth are acceptable if labeled

## Acceptance Criteria

### AC-008: Process-local RPM with honesty label
- **Scenario:** tenant `rpm_limit: 2`; three rapid authenticated requests
- **Action:** POST chat completions
- **Expected:** first two succeed (or reach worker); third returns 429; response includes `x-atlas-rpm-scope: process-local`
- **Must not:** claim distributed/production-safe limiting
- **Verification:** `uv run pytest platform/tenant/test_tenant_rpm.py platform/gateway/test_gateway_rpm.py`
- **Priority:** Required

### AC-009: Worker client stream timings
- **Scenario:** MockTransport returns two SSE content chunks then `[DONE]` with `id` in JSON
- **Action:** `stream_chat_completions`
- **Expected:** yields SSE lines; `ttft_ms` set after first `data:` JSON; `completion_ms` after `[DONE]`; `request_id` from chunk id; `status=ok`
- **Must not:** require a live GPU
- **Verification:** `uv run pytest workers/test_openai_worker_client.py`
- **Priority:** Required

### AC-010: Gateway upstream SSE passthrough
- **Scenario:** fake/stream-capable worker injected; `stream=true`
- **Action:** POST chat completions
- **Expected:** response body contains upstream chunk text and `[DONE]`; worker was invoked with `stream=True`
- **Must not:** only re-wrap a non-stream upstream call when client asked for stream
- **Verification:** gateway stream tests
- **Priority:** Required

### AC-011: Request-path Prometheus metrics + `/metrics`
- **Scenario:** one successful routed completion through gateway
- **Action:** GET `/metrics`
- **Expected:** text exposition includes counters/labels for tenant, strategy, worker_id, outcome; gauge `atlas_queue_depth`; cache signal; observed ttft/completion when provided
- **Must not:** increment metrics from a dashboard-only code path
- **Verification:** `uv run pytest platform/observability/test_atlas_metrics.py platform/gateway/test_gateway_metrics.py`
- **Priority:** Required

### AC-012: OTEL request span hook
- **Scenario:** chat completion runs with default TracerProvider
- **Action:** complete one request
- **Expected:** at least one finished span named `atlas.chat_completions` (or child) recorded in an in-memory exporter
- **Verification:** observability OTEL test
- **Priority:** Important

### AC-013: KEDA sketch + pin helper
- **Scenario:** repo files present
- **Action:** read `deploy/keda/atlas-queue-depth.yaml`; call pin helper
- **Expected:** ScaledObject triggers on Prometheus query of `atlas_queue_depth`; pin helper accepts `0.26.0` and rejects others
- **Must not:** imply the ScaledObject was applied to a live cluster
- **Verification:** file + unit tests
- **Priority:** Required

## Blocking Decisions

- None. Live GPU worker remains optional follow-up (Colab), not required to close Phase 4 offline.

## Verification Plan

| Criterion | Evidence | Status |
| --- | --- | --- |
| AC-001–007 | scaffold suite | PASS |
| AC-008 | tenant RPM + gateway RPM tests | PASS |
| AC-009–010 | worker stream + gateway passthrough | PASS |
| AC-011–012 | metrics + OTEL tests | PASS |
| AC-013 | KEDA YAML + pin helper tests | PASS |
