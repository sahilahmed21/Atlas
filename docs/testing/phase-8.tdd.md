# TDD evidence — Phase 8 prefix load gate

**Source plan:** `docs/phases/phase-8/ACCEPTANCE.md`  
**Runner:** `.venv-test` pytest (full `uv sync` blocked on torch download this session)

## User journeys

1. As a router owner, I want sticky prefix hits when the owner is cool so cache affinity still works.
2. As a platform owner, I want stickiness broken when the owner is hotter than an alternate by a configurable margin.
3. As an experimenter, I want a three-way high_reuse matrix (RR / sticky / gated) proving recovery.

## Task report

### RED
- New tests for `load_margin` / `hit_broken` / default-off; initially failed (`PrefixAwareRouter` rejected kwargs / cool scenario).
- Command: `pytest platform/router/test_router_strategies.py -k "sticky_when or breaks_when or miss_unchanged or default_margin"`

### GREEN
- Implemented gate + gateway `served_counts` + `--phase8` harness.
- Command: `pytest platform/router platform/gateway benchmarks/test_routing_matrix_harness.py -q` → **39 passed**
- Matrix: `python benchmarks/run_routing_matrix.py --phase8 --n 24` → gated p50 **147.5** vs sticky **297.5**

## Test specification

| # | Guarantee | Test | Result |
| --- | --- | --- | --- |
| 1 | Sticky when cool | `test_prefix_aware_sticky_when_owner_cool` | PASS |
| 2 | Break when hot → hit_broken | `test_prefix_aware_breaks_when_owner_hot` | PASS |
| 3 | Miss unchanged with gate | `test_prefix_aware_miss_unchanged_with_gate` | PASS |
| 4 | Default margin 0 keeps sticky | `test_prefix_aware_default_margin_zero_keeps_sticky_under_skew` | PASS |
| 5 | Gateway breaks under served pressure | `test_prefix_aware_load_gate_breaks_sticky_under_served_pressure` | PASS |
| 6 | Phase 8 three-way matrix | `test_phase8_gate_matrix_three_way` | PASS |

## Gaps

Live `--phase8 --worker-mode live` not run this session (optional). Full suite beyond platform/gateway/benchmarks harness not re-run (venv torch sync incomplete).
