# TDD evidence — Phase 5 routing experiment

**Source plan:** `~/.cursor/plans/phase_5_routing_design_a7ddcaeb.plan.md`  
**Acceptance:** [`docs/phases/phase-5/ACCEPTANCE.md`](../phases/phase-5/ACCEPTANCE.md) (rev 1)

## User journeys

1. As a platform owner, I want prefix affinity to claim owners and track in-flight load so routing strategies are meaningful.
2. As an experimenter, I want the same frozen traffic trace replayed under RR / least-load / prefix-aware with inspectable cache signals.
3. As a reviewer, I want ≥1 measured cell where prefix-aware loses, with an honest simulated-worker label and hypothesis.

## Task report

### Task: RED (AC-001–005 control loop)

- **Command:** `uv run pytest platform/router/test_router_strategies.py platform/gateway/test_gateway_routing_state.py -q --tb=line`
- **Result:** `4 failed` — missing `shared_prefix_key`, miss→lexicographic sticky, no owner/load write-back
- **Checkpoint:** `6b4bba6` `test: Phase 5 routing control-loop reproducers (RED)`

### Task: GREEN (control loop)

- **Command:** `uv run pytest platform workers -q`
- **Result:** `44 passed`
- **Guaranteed:** shared prefix key; miss→least-load claim; gateway owner write-back + hit; loads ±1 including stream path
- **Checkpoint:** `0ac1071` `feat: Phase 5 routing control loop — shared prefix, owner claim, loads (GREEN)`

### Task: Harness + matrix (AC-006–008)

- **Command:** `uv run pytest benchmarks/test_routing_matrix_harness.py -q` → `2 passed`
- **Runner:** `uv run python benchmarks/run_routing_matrix.py` → 12 CSV rows
- **Surprise:** high_reuse × prefix_aware TTFT p50 297.5 vs RR 147.5 despite 95.83% router hits

## Test specification

| # | Guarantee | Test | Result |
| --- | --- | --- | --- |
| 1 | Shared prefix ignores unique user | `test_shared_prefix_key_ignores_unique_user_suffix` | PASS |
| 2 | Miss claims via least-load | `test_prefix_aware_miss_claims_via_least_load` | PASS |
| 3 | Owner write-back + hit | `test_prefix_aware_owner_writeback_and_hit` | PASS |
| 4 | Loads clear after non-stream | `test_loads_return_to_zero_after_non_stream` | PASS |
| 5 | Stream decrements load | `test_stream_path_decrements_load` | PASS |
| 6 | In-flight load visible | `test_in_flight_load_visible_during_slow_upstream` | PASS |
| 7 | Hit TTFT < miss; load penalty | `test_simulated_worker_hit_faster_than_miss_and_load_penalty` | PASS |
| 8 | Matrix CSV same-trace rows | `test_matrix_runner_writes_csv_for_one_pattern` | PASS |

Evidence: `uv run pytest benchmarks platform workers -q` → `46 passed`.

## Coverage and known gaps

No coverage % tool. Deferred: live Colab dual-vLLM validation; TTFT load gate; standing-load least_load under sequential replay.

## Merge evidence / checkpoints

| Commit | Stage |
| --- | --- |
| `6b4bba6` test: Phase 5 routing control-loop reproducers (RED) | RED |
| `0ac1071` feat: Phase 5 routing control loop … (GREEN) | GREEN |
| *(this commit)* feat: Phase 5 offline routing matrix + harness | matrix |
