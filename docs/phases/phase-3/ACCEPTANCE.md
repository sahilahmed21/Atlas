# Acceptance Brief: Phase 3 vLLM reconciliation

**Status:** Implemented + verified (AC-005 Colab T4)  
**Revision:** 3  
**Approval required before risky work:** No for offline harness/plot/source-diff; inventing GPU numbers forbidden

## Goal

Reconcile Phase 1 naive HF load against a pinned vLLM run on Colab/Kaggle T4, with one overlay chart and a source-level toy-vs-vLLM diff — without inventing measurements.

## Scope

**In scope**
- Pin `vllm==0.26.0` and document Colab T4 install (`+cu129` wheel when driver is CUDA 12.x)
- Same load-shape philosophy as Phase 1 → `results/phase3/vllm_load.csv` (produced on GPU host)
- Overlay chart → `results/phase3/naive_vs_vllm.png`
- Caption + source reconciliation in `01_before_after.md` / `02_source_diff.md`
- Thin Colab notebook that calls repo Python

**Out of scope**
- Phase 4 platform / router
- Fake or synthetic “measured” latency/VRAM in committed result CSVs
- Claiming Phase 2 sims explain Phase 1 or Phase 3 GPU metrics

## Assumptions

- Hardware for the real sweep is Colab or Kaggle T4 (not native Windows)
- Model family stays Qwen2.5-0.5B @ revision `7ae5576` unless VRAM forces a documented downsize
- Concurrency sweep `[1, 2, 4, 8]`, `max_new_tokens=32` first (match Phase 1 cliff-stop philosophy)
- Test runner: `uv run pytest` (offline; no GPU required for unit tests)

## Acceptance Criteria

### AC-001: vLLM version pinned and recorded
- **Scenario:** Repo dependency metadata and reading list
- **Action:** Inspect `pyproject.toml` + `docs/knowledge/vllm-internals/READING_LIST.md`
- **Expected:** Exact version `0.26.0` in harness + config + READING_LIST; Colab T4 note names the `+cu129` wheel. (`pyproject.toml` `gpu` group stays empty — declaring `vllm==0.26.0` breaks laptop uv resolve vs cu124 torch index.)
- **Must not:** Leave the pin undocumented or invent GPU CSVs
- **Verification:** Manual doc/dep review + `PINNED_VLLM_VERSION == "0.26.0"` in tests
- **Priority:** Required

### AC-002: Overlay plot joins Phase 1 + Phase 3 CSVs
- **Scenario:** Fixture naive + vllm CSVs with matching schema and concurrency points
- **Action:** Run overlay plotter
- **Expected:** Writes PNG; both series present; missing vllm CSV raises clearly
- **Must not:** Fabricate vLLM rows when CSV absent
- **Verification:** `uv run pytest fundamentals/experiments/test_plot_naive_vs_vllm.py`
- **Priority:** Required

### AC-003: Load harness preserves Phase 1 CSV contract
- **Scenario:** Offline construction of a result row (no GPU)
- **Action:** Build a row via harness helpers
- **Expected:** Same field names as Phase 1; notes include pinned vLLM version string
- **Must not:** Require GPU to unit-test schema
- **Verification:** `uv run pytest fundamentals/experiments/test_vllm_load.py`
- **Priority:** Required

### AC-004: Source reconciliation cites pinned tag
- **Scenario:** Phase 2 toys vs vLLM `v0.26.0` sources/docs
- **Action:** Fill `02_source_diff.md`
- **Expected:** 3 similarities, 3 differences, 1 toy misunderstanding; file:line or design-doc paths under tag `v0.26.0`
- **Must not:** Cite “latest” without a pin
- **Verification:** Manual review of `02_source_diff.md`
- **Priority:** Required

### AC-005: Real GPU artifact (Colab/Kaggle)
- **Scenario:** T4 runtime with pinned wheel + same model revision
- **Action:** Run notebook/harness; write `vllm_load.csv`; regenerate overlay; caption `01_before_after.md`
- **Expected:** Measured rows only; chart exists; caption states version/hardware/TTFT proxy honesty
- **Must not:** Commit invented timings
- **Verification:** Files present under `results/phase3/` after GPU run; human review of caption
- **Environment/safety:** Colab/Kaggle only; no secrets
- **Priority:** Required (blocks Phase 4)

## Blocking Decisions

- [x] Pin target: **0.26.0** (GitHub release 2026-07-27; verified)
- [x] T4 install: prefer **`vllm-0.26.0+cu129-...`** when host lacks CUDA 13 runtime (verified via release assets + install guidance)
- [ ] GPU host available in this session? If no → complete AC-001–004 offline; leave AC-005 pending with empty `results/phase3/` until Colab run

## Verification Plan

| Criterion | Evidence | Status |
| --- | --- | --- |
| AC-001 | READING_LIST + PINNED_VLLM_VERSION + phase3.yaml (pyproject gpu empty — resolve conflict) | Done |
| AC-002 | `uv run pytest fundamentals/experiments/test_plot_naive_vs_vllm.py` → 4 passed | Done |
| AC-003 | `uv run pytest fundamentals/experiments/test_vllm_load.py` → 4 passed | Done |
| AC-004 | 02_source_diff.md @ tag v0.26.0 | Done |
| AC-005 | `results/phase3/vllm_load.csv` + `naive_vs_vllm.png` + `01_before_after.md` (Colab T4) | Done |
