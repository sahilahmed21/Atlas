# TDD evidence — Phase 4 platform scaffolding

**Source plan:** [`docs/phases/phase-4/README.md`](../phases/phase-4/README.md)  
**Acceptance:** [`docs/phases/phase-4/ACCEPTANCE.md`](../phases/phase-4/ACCEPTANCE.md)

## User journeys

1. As a client, I want `POST /v1/chat/completions` with an API key so I get an OpenAI-shaped completion from a routed worker.
2. As a platform engineer, I want invalid/auth failures rejected at the gateway without calling a worker.
3. As a routing engineer, I want round_robin / least_load / prefix_aware decisions with non-empty reasons for Phase 5.
4. As a worker owner, I want a thin client that POSTs to `{base_url}/chat/completions` without tenant logic.

## Task report

### Task: RED reproducers (AC-001–007)

- **Summary:** Added failing tests under `platform/*` and `workers/` before implementations existed.
- **RED command:** `uv run pytest platform workers -q --tb=line`
- **RED result:** `20 failed` — `ModuleNotFoundError` for `app` / `tenants` / `workers_registry` / `strategies` / `openai_worker_client` (intended missing-impl RED). One async-mark failure on worker client was converted to sync before GREEN.
- **Guaranteed:** Tests compile and execute; failure mode is missing production modules.

### Task: GREEN scaffold

- **Summary:** Minimal YAML tenant/registry, three routers, OpenAI worker client, FastAPI gateway with fake-worker injection + scaffold SSE.
- **GREEN command:** `uv run pytest platform workers -q`
- **GREEN result:** `20 passed`
- **Guaranteed:** Auth → route → fake worker path; route headers; prefix hit/fallback reasons; no GPU required.

## Test specification

| # | What is guaranteed | Test | Result |
| --- | --- | --- | --- |
| 1 | Valid chat returns completion + route headers | `test_gateway_chat.py::test_chat_completions_ok_with_route_decision` | PASS |
| 2 | Missing messages → 400, no worker call | `test_chat_completions_rejects_missing_messages` | PASS |
| 3 | Missing model → 400 | `test_chat_completions_rejects_missing_model` | PASS |
| 4 | Bad key → 401; secrets not echoed | `test_chat_completions_unauthorized` | PASS |
| 5 | Disallowed model → 403 | `test_chat_completions_rejects_disallowed_model` | PASS |
| 6 | `stream=true` yields SSE + `[DONE]` | `test_streaming_returns_sse_chunks` | PASS |
| 7–10 | Tenant YAML load + authenticate | `test_tenant_auth.py` | PASS |
| 11–13 | Worker registry resolve-by-model | `test_worker_registry.py` | PASS |
| 14–18 | RR / least-load / prefix hit+fallback / empty | `test_router_strategies.py` | PASS |
| 19–20 | Worker client POST path + HTTP error | `test_openai_worker_client.py` | PASS |

Evidence command: `uv run pytest platform workers -q` → `20 passed`.

## Coverage and known gaps

No coverage tool run. Intentionally deferred: real vLLM wiring, process-local RPM enforcement, Prometheus/OTEL, least-load live queue depth from workers, true token streaming from upstream, distributed prefix index.

## Merge evidence / checkpoints

| Stage | Evidence |
| --- | --- |
| RED | `20 failed` ModuleNotFoundError before impl (session log) |
| GREEN | `20 passed` after scaffold |
