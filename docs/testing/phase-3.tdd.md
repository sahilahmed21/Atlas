# TDD evidence — Phase 3 vLLM reconciliation (offline slice)

**Source plan:** [`docs/phases/phase-3/README.md`](../phases/phase-3/README.md)  
**Acceptance:** [`docs/phases/phase-3/ACCEPTANCE.md`](../phases/phase-3/ACCEPTANCE.md)

## User journeys

1. As an engineer, I want an overlay plotter that joins Phase 1 + Phase 3 CSVs so the eye-stopper chart cannot invent missing vLLM points.
2. As an engineer, I want the vLLM load harness to share Phase 1’s CSV contract and embed the pinned version in every row.
3. As an engineer, I want a source diff against tag `v0.26.0` so Phase 2 toys are not oversold as APC.

## Task report

### Task: Overlay join + plot (AC-002)

- **Summary:** `pair_by_concurrency` intersects ok rows; `plot_overlay` writes PNG; missing vLLM CSV → `FileNotFoundError`.
- **RED:** `uv run pytest fundamentals/experiments/test_plot_naive_vs_vllm.py -q` → `ModuleNotFoundError: No module named 'plot_naive_vs_vllm'` (4 failed)
- **GREEN:** same command → `4 passed`
- **Guaranteed:** Only overlapping concurrency points are paired; absence of vLLM CSV does not fabricate rows.

### Task: Load harness contract (AC-003)

- **Summary:** `CSV_FIELDS` match Phase 1; `build_row` embeds `vllm=0.26.0`; pin assert rejects mismatches; config loader reads `phase3.yaml` keys.
- **RED:** `ModuleNotFoundError: No module named 'vllm_load'` (4 failed)
- **GREEN:** `4 passed`
- **Guaranteed:** Offline schema/pin without importing a GPU runtime in the happy path of helpers.

### Task: Pin + source diff (AC-001, AC-004)

- **Summary:** Pin `0.26.0` in harness + config + READING_LIST; Colab T4 uses `+cu129` wheel (verified against release assets). `pyproject.toml` `gpu` group left empty — declaring `vllm==0.26.0` breaks laptop `uv` resolve against the cu124 torch index (`torch==2.11.0` not on that index).
- **Verification:** Manual review of READING_LIST + `02_source_diff.md`.

### Task: GPU artifact (AC-005)

- **Status:** Pending Colab/Kaggle. No invented `results/phase3/*.csv|png`.

## Test specification

| # | What is guaranteed | Test | Type | Result | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Naive/vLLM ok rows join on concurrency | `test_pair_by_concurrency_aligns_ok_rows` | unit | PASS | `uv run pytest fundamentals/experiments/test_plot_naive_vs_vllm.py` |
| 2 | Missing side drops the point | `test_pair_by_concurrency_skips_points_missing_on_one_side` | unit | PASS | same |
| 3 | Missing vLLM CSV raises | `test_missing_vllm_csv_raises` | unit | PASS | same |
| 4 | Overlay writes non-empty PNG | `test_plot_writes_png` | unit | PASS | same |
| 5 | CSV fields == Phase 1 | `test_csv_fields_match_phase1` | unit | PASS | `uv run pytest fundamentals/experiments/test_vllm_load.py` |
| 6 | Row notes include pin | `test_build_row_embeds_pinned_vllm_version` | unit | PASS | same |
| 7 | Runtime pin mismatch errors | `test_assert_runtime_vllm_matches_pin` | unit | PASS | same |
| 8 | phase3.yaml keys load | `test_load_phase3_config_requires_same_revision_keys` | unit | PASS | same |

## Coverage and known gaps

No coverage tool. Deliberate gaps: live `LLM.generate` path, ThreadPoolExecutor concurrency under GPU, streaming TTFT (documented proxy), AC-005 GPU artifacts.

## Merge evidence / checkpoints

| Commit message | Stage |
| --- | --- |
| `test: add Phase 3 overlay and vLLM load reproducers (RED)` | RED |
| `feat: Phase 3 overlay plotter, vLLM harness, pin 0.26.0 (GREEN)` | GREEN (this close-out) |
