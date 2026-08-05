# TDD evidence — Phase 1 failure curve

**Source plan:** [`docs/phases/phase-1/START_HERE.md`](../phases/phase-1/START_HERE.md) (AC-001–AC-004).
No `*.plan.md` was supplied; journeys derive from the phase acceptance criteria.

## User journeys

1. As an engineer reproducing Phase 1, I want to regenerate the failure curve from the committed CSV
   alone, so that the eye-stopper chart is verifiable rather than asserted.
2. As a reviewer, I want the "latency cliff" claim to be computed by tested code, so that the
   headline number in `03_failure_curve.md` is not eyeballed off a graph.

## Task report

### Task: classify failure points in the sweep CSV

- **Summary:** Added `load_runs` / `mark_failures` in `fundamentals/experiments/plot_failure_curve.py`,
  driven by tests written first.
- **RED command:** `uv run pytest fundamentals/experiments/test_plot_failure_curve.py -q`
- **RED output:**
  ```
  E   ModuleNotFoundError: No module named 'plot_failure_curve'
  1 error in 0.27s
  ```
  Compile-time RED: the test references the not-yet-existing classification module. No production
  code existed to edit before this gate.
- **GREEN command:** `uv run pytest fundamentals/experiments/test_plot_failure_curve.py -q`
- **GREEN output:**
  ```
  ....                                                                     [100%]
  4 passed in 3.61s
  ```
- **Guaranteed by the passing tests:** rows are ordered by concurrency with numeric fields parsed;
  an `oom` row is flagged even when it has no timings; a cliff is only claimed when a run exceeds
  `cliff_factor ×` the measured N=1 baseline; with no N=1 baseline present, nothing is called a cliff.

### Task: render the chart artifact

- **Summary:** `plot()` writes a two-panel latency + peak-VRAM figure with the cliff point circled.
- **Command:** `uv run python fundamentals/experiments/plot_failure_curve.py`
- **Output excerpt:**
  ```
  N=1   total_ms=1670.764 peak_vram_mb=969.2  failure=None
  N=8   total_ms=9242.146 peak_vram_mb=1042.9 failure=cliff
  wrote C:\projects\Atlas\results\phase1\oom_latency_curve.png
  ```
- **Verification:** manual visual check of the rendered PNG (axes labelled, cliff marked, hardware and
  model in title) — automation would be disproportionate for figure aesthetics.

## Test specification

| # | What is guaranteed | Test | Type | Result | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Runs are sorted by concurrency and numeric fields parsed as numbers | `test_load_runs_sorts_by_concurrency_and_parses_numbers` | unit | PASS | `uv run pytest fundamentals/experiments` |
| 2 | An OOM row is flagged even with empty latency columns | `test_oom_row_is_marked_even_without_timings` | unit | PASS | same |
| 3 | A latency cliff is measured against the N=1 baseline, not an absolute threshold | `test_latency_cliff_is_measured_against_the_n1_baseline` | unit | PASS | same |
| 4 | Without an N=1 baseline no cliff is claimed | `test_no_baseline_means_no_cliff_claim` | unit | PASS | same |

## Coverage and known gaps

No coverage tool is configured in this repo and none was added — the tested surface is two functions.
Deliberately untested:

- **Figure rendering.** Verified by opening the PNG. Asserting on matplotlib artists tests the library,
  not the finding.
- **`naive_hf_load.py`.** It is a GPU-bound measurement harness whose output *is* the artifact under
  review; its correctness is evidenced by the CSV and the memory math agreeing within 3% on the
  weights term, not by unit tests.

## Merge evidence

RED: `ModuleNotFoundError` on the classification module (4 tests uncollectable).
GREEN: 4 passed after implementing `load_runs` / `mark_failures`.
Refactor: none required; implementation was written minimal and left unchanged.

No checkpoint commits were created — the working tree also carries unrelated pending changes
(`docker-compose.obs.yml`, `configs/observability/`, `scripts/verify_wsl_vllm.py`) from earlier work,
and committing was not requested. This report is the durable RED/GREEN record.
