# Acceptance Brief: Phase 4 scaffolding (gateway + router)

**Status:** Implemented (scaffold) — AC-001–007 evidenced offline with fake worker  
**Revision:** 1  
**Approval required before risky work:** No — laptop/fake-worker only; inventing live metrics forbidden

## Goal

A local client can authenticate, route, and complete one OpenAI-compatible chat request through the gateway to an explicitly labeled fake worker, with inspectable route decisions.

## Scope

**In scope**
- FastAPI `POST /v1/chat/completions` (non-stream + stream) with documented 4xx error shape
- YAML tenants (API key → tenant id; allowed models)
- YAML worker registry (model → workers)
- Router strategies: round_robin, least_load, prefix_aware — each emits `worker_id`, `strategy`, `reason`
- Thin worker client POSTing to a worker's OpenAI-compatible `/v1/chat/completions`
- Fake-worker integration test (no GPU)

**Out of scope**
- Real vLLM process / Colab GPU wiring
- Prometheus / OTEL / dashboard metrics (hooks later)
- Production-safe distributed RPM limiter (process-local only if present; must be labeled)
- Autoscaling / KEDA / multi-node
- Invented cache-hit or TTFT dashboard numbers

## Assumptions

- API key via `Authorization: Bearer <key>`
- Workers are OpenAI-compatible HTTP servers; tests inject a fake client
- Prefix-aware uses an injected local `prefix_hash → worker_id` map (no distributed cache index)
- Test runner: `uv run pytest platform workers -q`

## Acceptance Criteria

### AC-001: Valid chat completion through gateway + fake worker
- **Scenario:** known API key, allowed model, fake worker injected
- **Action:** `POST /v1/chat/completions` with messages
- **Expected:** HTTP 200; body has `object=chat.completion`, `choices[0].message.content`, and response header or body field exposing route decision reason
- **Must not:** call a real GPU worker
- **Verification:** `uv run pytest platform/gateway/test_gateway_chat.py`
- **Priority:** Required

### AC-002: Invalid request rejected at boundary
- **Scenario:** authenticated request missing `messages` or `model`
- **Action:** `POST /v1/chat/completions`
- **Expected:** HTTP 400 with OpenAI-ish `error.message` / `error.type`
- **Must not:** forward to worker
- **Verification:** same gateway tests
- **Priority:** Required

### AC-003: API key auth
- **Scenario:** YAML tenant registry with one key
- **Action:** authenticate with valid vs unknown key
- **Expected:** valid → tenant id; unknown → HTTP 401 from gateway
- **Must not:** log the raw API key in returned errors
- **Verification:** tenant + gateway tests
- **Priority:** Required

### AC-004: Registry resolves workers by model
- **Scenario:** two workers sharing a model id in YAML
- **Action:** resolve by model
- **Expected:** both workers returned; unknown model → empty list
- **Verification:** `uv run pytest platform/registry/test_worker_registry.py`
- **Priority:** Required

### AC-005: Round-robin + least-load emit reasons
- **Scenario:** ≥2 eligible workers
- **Action:** choose repeatedly / with uneven loads
- **Expected:** RR cycles; least-load picks lowest load; each decision has non-empty `reason`
- **Verification:** `uv run pytest platform/router/test_router_strategies.py`
- **Priority:** Required

### AC-006: Prefix-aware hit and deterministic fallback
- **Scenario:** known prefix hash owned by worker-b; unknown prefix
- **Action:** choose with prompt
- **Expected:** hit → worker-b + reason mentions prefix; miss → deterministic fallback + reason mentions fallback
- **Verification:** same router tests
- **Priority:** Required

### AC-007: Worker client posts OpenAI chat path
- **Scenario:** httpx mock / ASGI transport
- **Action:** `chat_completions(payload)`
- **Expected:** `POST {base_url}/chat/completions` (base_url already includes `/v1`); returns JSON body
- **Verification:** `uv run pytest workers/test_openai_worker_client.py`
- **Priority:** Required

## Blocking Decisions

- None for scaffolding. Streaming shape may be minimal SSE chunks labeled as scaffold.

## Verification Plan

| Criterion | Evidence | Status |
| --- | --- | --- |
| AC-001–003 | `platform/gateway/test_gateway_chat.py` + tenant tests | PASS |
| AC-004 | `platform/registry/test_worker_registry.py` | PASS |
| AC-005–006 | `platform/router/test_router_strategies.py` | PASS |
| AC-007 | `workers/test_openai_worker_client.py` | PASS |
