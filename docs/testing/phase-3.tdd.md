# TDD evidence — Phase 3 vLLM reconciliation (offline slice)

**Source plan:** [`docs/phases/phase-3/README.md`](../phases/phase-3/README.md)  
**Acceptance:** [`docs/phases/phase-3/ACCEPTANCE.md`](../phases/phase-3/ACCEPTANCE.md)  
**Review fixes:** Critical/High from Phase 0–3 code review (CB batching, suffixes, NVML, hardware labels, gitignore, install docs)

## User journeys

1. As an engineer, I want an overlay plotter that joins Phase 1 + Phase 3 CSVs so the eye-stopper chart cannot invent missing vLLM points.
2. As an engineer, I want the vLLM load harness to share Phase 1’s CSV contract and embed the pinned version in every row.
3. As an engineer, I want a source diff against tag `v0.26.0` so Phase 2 toys are not oversold as APC.
4. As an engineer, I want Phase 3 concurrency to be one batched `generate([p0..pN-1])` with Phase 1 `[req=i]` suffixes so the chart measures continuous batching, not thread queueing.
5. As an engineer, I want NVML VRAM and labeled cross-hardware overlays so meters and hosts stay honest.

## Task report

### Task: Overlay join + plot (AC-002) + hardware honesty

- **Summary:** Pairs carry `naive_hardware` / `vllm_hardware`; `overlay_title` marks cross-hardware.
- **RED (honesty):** missing keys / `overlay_title` ImportError / bare `models/` in gitignore
- **GREEN:** `14 passed` in experiments Phase 3 tests; full fundamentals `25 passed`
- **Guaranteed:** No fabricated vLLM rows; title always names both hardwares.

### Task: Load harness contract (AC-003) + CB / NVML

- **Summary:** `make_prompts` + single `llm.generate(prompts)`; `peak_vram_mb` via `pynvml`; notes `ttft_proxy=batch_wall; vram_source=nvml`.
- **RED:** threaded path → 0 FakeLLM batched calls; torch VRAM path; no `make_prompts`
- **GREEN:** FakeLLM receives exactly one call with `[req=0..3]`; NVML mock returns 2048 MB
- **Guaranteed:** Offline CB contract without live GPU.

### Task: Pin + install path (AC-001)

- **Summary:** `gpu` group empty; runbooks/README/HANDOFF/verify script use `+cu129` + pin assert.
- **Verification:** docs + `scripts/verify_wsl_vllm.py` imports `assert_runtime_vllm_matches_pin`.

### Task: GPU artifact (AC-005)

- **Status:** Pending Colab/Kaggle. No invented `results/phase3/*.csv|png`.

## Test specification

| # | What is guaranteed | Test | Result |
| --- | --- | --- | --- |
| 1–4 | Overlay join / missing CSV / PNG / hardware fields | `test_plot_naive_vs_vllm.py` | PASS |
| 5 | Cross-hardware title warns | `test_overlay_title_labels_cross_hardware` | PASS |
| 6 | Same-hardware title has no cross warning | `test_overlay_title_same_hardware_has_no_cross_warning` | PASS |
| 7 | `/models/` only (not bare `models/`) | `test_gitignore_models_rule_is_repo_root_only` | PASS |
| 8–11 | CSV/pin/config helpers | `test_vllm_load.py` (original) | PASS |
| 12 | Unique `[req=i]` prompts | `test_make_prompts_match_phase1_unique_suffixes` | PASS |
| 13 | One batched generate | `test_run_concurrent_single_batched_generate_with_unique_prompts` | PASS |
| 14 | NVML VRAM path | `test_peak_vram_mb_uses_nvml_not_torch` | PASS |

Evidence command: `uv run pytest fundamentals/experiments fundamentals/allocators fundamentals/schedulers fundamentals/prefix_cache -q` → `25 passed`.

## Coverage and known gaps

No coverage tool. Still untested live: real `LLM.generate` on GPU, NVML on host without GPU (returns None), AC-005 artifacts. Streaming TTFT still a documented proxy (`batch_wall`).

## Merge evidence / checkpoints

| Commit message | Stage |
| --- | --- |
| `test: add Phase 3 overlay and vLLM load reproducers (RED)` | RED (initial) |
| `feat: Phase 3 overlay plotter, vLLM harness, pin 0.26.0 (GREEN)` | GREEN (initial) |
| `test: reproduce Phase 3 CB/VRAM/hardware honesty bugs (RED)` | RED (review fixes) |
| `fix: Phase 3 batch generate, NVML VRAM, hardware honesty (GREEN)` | GREEN (review fixes) |
