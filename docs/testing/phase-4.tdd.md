# TDD evidence — Phase 4 platform end-to-end

**Source plan:** [`docs/phases/phase-4/README.md`](../phases/phase-4/README.md)  
**Acceptance:** [`docs/phases/phase-4/ACCEPTANCE.md`](../phases/phase-4/ACCEPTANCE.md) (rev 2)

## User journeys

1. As a tenant, I want RPM enforced with an honest `process-local` label so I am not misled about multi-replica safety.
2. As a client, I want `stream=true` to pass through upstream SSE with measurable TTFT from the worker client.
3. As a dashboard (Phase 5.5), I want `/metrics` populated by the same request path that served the completion.
4. As an operator, I want a KEDA sketch keyed on `atlas_queue_depth` marked as planning-only, plus a pin helper for vLLM `0.26.0`.

## Task report

### Task: RED (AC-008–013)

- **Command:** `uv run pytest platform/tenant/test_tenant_rpm.py platform/gateway/test_gateway_rpm.py platform/gateway/test_gateway_metrics.py platform/observability platform/autoscaling workers/test_openai_worker_client.py::test_stream_chat_completions_records_ttft_and_request_id -q --tb=line`
- **Result:** `12 failed` — missing `rpm` / `atlas_metrics` / `otel_hooks` / `vllm_pin` / KEDA file / `stream_chat_completions`; gateway still re-wrapped non-stream for SSE; RPM not enforced
- **Checkpoint:** `dcaa927` `test: Phase 4 remaining E2E reproducers (RED)`

### Task: GREEN

- **Command:** `uv run pytest platform workers -q`
- **Result:** `32 passed`
- **Guaranteed:** RPM 429 + scope header; upstream SSE passthrough; Prometheus from request path; OTEL span; KEDA sketch; vLLM pin helper; stream timings

### Verification note

Exa MCP was **not** configured in this environment. Contracts verified via web search: `generate_latest` for `/metrics` (avoid mount redirect), OpenAI/vLLM SSE `data:` + `[DONE]`, KEDA Prometheus trigger on queue depth.

## Test specification

| # | Guarantee | Test | Result |
| --- | --- | --- | --- |
| 1–3 | Process-local RPM window + honesty constant | `test_tenant_rpm.py` | PASS |
| 4 | 3rd request → 429 + `x-atlas-rpm-scope` | `test_gateway_rpm.py` | PASS |
| 5–6 | Metrics labels + queue gauge | `test_atlas_metrics.py` | PASS |
| 7 | OTEL `atlas.chat_completions` span | `test_otel_hooks.py` | PASS |
| 8–9 | `/metrics` after request; SSE passthrough | `test_gateway_metrics.py` | PASS |
| 10–11 | KEDA sketch + pin `0.26.0` | `test_keda_sketch.py` | PASS |
| 12 | Stream TTFT / request_id timings | `test_openai_worker_client.py` | PASS |
| 13–32 | Prior scaffold AC-001–007 suite | gateway/tenant/registry/router/worker | PASS |

Evidence: `uv run pytest platform workers -q` → `32 passed`.

## Coverage and known gaps

No coverage % tool. Still deferred: live Colab vLLM behind gateway, distributed RPM, true multi-replica queue depth, applying KEDA to a cluster.

## Merge evidence / checkpoints

| Commit | Stage |
| --- | --- |
| `dcaa927` test: Phase 4 remaining E2E reproducers (RED) | RED |
| `328e512` feat: Phase 4 RPM, metrics, stream passthrough, KEDA sketch (GREEN) | GREEN |
