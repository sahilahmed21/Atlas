# Agent flight recorder

The gateway can record every LLM call an agent makes (a *run*), replay the run byte-for-byte without calling a model, and inject seeded faults. Recording is off unless `ATLAS_RECORDER_DB` is set and the tenant has `record_allowed: true`.

## Request headers (on `POST /v1/chat/completions`)

| Header | Meaning |
| --- | --- |
| `x-atlas-mode` | `live` (default, no recording), `record`, or `replay` |
| `x-atlas-run-id` | 1-128 chars of `A-Z a-z 0-9 . _ : / -`. Required for record/replay. Namespaced per tenant. |
| `x-atlas-step` | Non-negative integer, required for record/replay. The client owns step numbering. |
| `x-atlas-fault-seed` | Integer. Record mode only (`400` otherwise; ignored in replay). |
| `x-atlas-fault-rate` | `0..1`, default `0.25`. |

The body is forwarded to the worker unchanged (tools, tool_calls, `content: null`, any OpenAI field). The request is hashed as canonical JSON (sorted keys, compact separators).

## Behaviour

| Situation | Result |
| --- | --- |
| Record, new step | Call the worker, store the step, return the response. The step is committed before the response is returned (streams: when the upstream stream ends). |
| Record, same step + same request again | Served from the store; the worker is **not** called again (idempotent retry). `x-atlas-replay: 1`. |
| Record, same step + different request | `409 run_step_conflict`; the original is untouched. |
| Record, step in a closed run | `409 run_closed` (already-recorded steps are still served). |
| Replay, matching step | Stored bytes, status and (for streams) SSE events. The worker client is never touched. |
| Replay, step missing | `404 replay_step_missing` with `run_status` (`incomplete` means a step was lost). |
| Replay, request differs | `409 replay_divergence` with `step`, `expected_hash`, `actual_hash`. |
| Upstream failure while recording | Recorded as the step's result (`502`), so replay reproduces it. |
| Recorder unavailable | `503 recorder_unavailable`, counted in `atlas_recorder_errors_total{kind}`. |
| Client disconnects mid-stream, or stream exceeds `ATLAS_RECORD_MAX_BYTES` | The live client is unaffected; the run is flagged `incomplete` and replay of the missing step returns `404`. |

Faults (`fault_for(seed, step, rate)`, a pure function): `rate_limit` (429), `server_error` (503), `timeout` (504), `malformed_json`, `truncated_stream`. They replace the worker call, are stored with `fault=<kind>`, and replay needs no seed. A latency-spike fault is deliberately not offered: it depends on wall-clock time and cannot be byte-identical.

## Run API (tenant-scoped, `record_allowed` required)

- `GET /atlas/runs/{run_id}`: status (`open|closed|incomplete`) and per-step summaries (hash, outcome, worker, timings, token counts, fault). **No prompt or response text.**
- `POST /atlas/runs/{run_id}/end`: `open -> closed`. An `incomplete` run stays `incomplete`.

## Storage (`ATLAS_RECORDER_DB`, one SQLite file, WAL)

- `runs(tenant_id, run_id, created_at, status)` PK `(tenant_id, run_id)`.
- `steps(tenant_id, run_id, step, req_hash, req_body, resp_status, resp_body, is_stream, worker_id, ttft_ms, completion_ms, prompt_tokens, completion_tokens, fault, outcome, ts)` PK `(tenant_id, run_id, step)`, FK to `runs`.
- One writer thread owns the connection; `PRAGMA user_version` guards the schema version. Stored runs contain prompt and response text, so they are the only content store: events, metrics and traces never carry it. Retention: `python platform/recorder/purge.py <db> <days>` deletes runs older than N days with their steps (schedule it; safe while the gateway runs).

## Configuration

| Env var | Meaning |
| --- | --- |
| `ATLAS_RECORDER_DB` | Path to the SQLite file; unset = recording disabled (`400 recording_disabled`). |
| `ATLAS_RECORD_MAX_BYTES` | Per-stream recording cap (default 8 MiB). |
| `ATLAS_ALLOW_QUERY_KEY=1` | Demo only: accept `?api_key=` on the event endpoints (the dashboard's EventSource cannot set headers). |
| `OTEL_EXPORTER_OTLP_ENDPOINT` / `ATLAS_OTEL_CONSOLE=1` | Export gateway spans (`atlas.chat_completions`, with tenant, worker, outcome). Off by default. |
| `api_key_env` in `workers.yaml` | Name of the env var holding a worker's upstream API key; the gateway refuses to start if it is unset. |

## Recording overhead (measured)

`python benchmarks/recorder_overhead.py <concurrent_runs> <steps>`: in-process ASGI, instant fake upstream, so this is the gateway + SQLite cost only, on a Windows laptop:

| Concurrent runs | Added p50 latency per request |
| --- | --- |
| 1 | about +0.7 ms |
| 10 | about +37 ms |
| 50 | about +105 ms |

The cost grows with concurrency because all commits go through one writer. Group commit is the known fix; it is not built because no latency budget requires it yet. A real model call (hundreds of ms or more) dominates these numbers at low concurrency.

## Limits

- One gateway replica per recorder file. RPM and the event ring are also process-local.
- A worker call whose response is lost before commit (crash, or a commit failure after the call) is not recoverable: the client's retry calls the worker again.
- Two concurrent identical steps may both reach the worker; the loser is answered with the winner's stored response.
- Replay guarantees byte-identical *gateway* output. An agent's final answer is identical only if the agent itself is deterministic given those responses (a changed request shows up as `replay_divergence`).

## Eval harness (`evals/`)

`python evals/demo.py` runs the whole loop offline. The pieces: `dataset.py` (seeded synthetic data), `tasks.py` (32 SQL tasks, ground truth computed from the data, outcome grader), `sql_tool.py` (read-only, row- and time-capped), `agent.py` (reference tool-calling loop), `runner.py` (k trials per task, bounded concurrency, one recorded run per trial), `report.py` (pass@1, pass@k, pass^k with task-level bootstrap CIs; flaky tasks; failure tags; cost/latency from the run log), `gate.py` (paired regression gate: fails only when the 95% CI of the pass^k delta is entirely below zero; `first_divergence` finds the first step where two runs' requests differ).

`scripted_model.py` is a deterministic stand-in for an LLM used to validate this pipeline. **Its numbers say nothing about any real model.** To evaluate a real model, point a worker in `workers.yaml` at it, set `api_key_env`, and run the same runner against the gateway; that spike (tool-calling support, temperature-0 variance, cost per task) has not been run.
