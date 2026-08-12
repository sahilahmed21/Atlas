# TDD evidence — Phase 7 live routing harness

**Source plan:** journeys from `docs/phases/phase-7/ACCEPTANCE.md` + this session (Step A harness only; GPU run is manual).  
**Acceptance (code slice):** AC-001 readiness — live path uses `OpenAIWorkerClient` + streaming; no `SimulatedWorkerClient` for live rows.

## User journeys

1. As an experimenter, I want high_reuse replayed under RR vs prefix_aware against OpenAI-compatible workers with streaming TTFT so Phase 7 can validate the GPU surprise.
2. As a reviewer, I want CSV rows labeled `worker_mode=live` with hardware / vllm_version / replica_mode metadata.

## Task report

### Task: RED (live harness kwargs + metadata)

- **Command:** `uv run pytest benchmarks/test_routing_matrix_harness.py::test_live_matrix_writes_metadata_and_streaming_ttft -q --tb=short`
- **Result:** `1 failed` — `TypeError: run_matrix() got an unexpected keyword argument 'worker_mode'`
- **Checkpoint:** `d8ed511` `test: Phase 7 live routing matrix harness reproducer (RED)`

### Task: GREEN (live mode + CLI)

- **Command:** `uv run pytest benchmarks/test_routing_matrix_harness.py -q` → `3 passed`
- **Full:** `uv run pytest platform workers benchmarks -q` → `53 passed`
- **Guaranteed:** `--worker-mode live` streams; MockTransport path records TTFT; CSV carries live metadata; sim path unchanged
- **Checkpoint:** `517a309` `feat: Phase 7 live routing matrix harness (GREEN)`

## Test specification

| # | What is guaranteed | Test | Result |
| --- | --- | --- | --- |
| 1 | Sim hit faster than miss + load penalty | `test_simulated_worker_hit_faster_than_miss_and_load_penalty` | PASS |
| 2 | Sim matrix CSV for one pattern | `test_matrix_runner_writes_csv_for_one_pattern` | PASS |
| 3 | Live mode streams, metadata CSV, not SimulatedWorkerClient | `test_live_matrix_writes_metadata_and_streaming_ttft` | PASS |

## Coverage and known gaps

No coverage % tool. **Intentional gap:** real Colab dual-vLLM evidence (AC-001–006 full) — requires manual GPU session; harness only proves the live *path*. Do not invent GPU numbers.

## Merge evidence / checkpoints

| Commit | Stage |
| --- | --- |
| `d8ed511` test: Phase 7 live routing matrix harness reproducer (RED) | RED |
| `517a309` feat: Phase 7 live routing matrix harness (GREEN) | GREEN |
