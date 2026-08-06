# vLLM internals — reading list

**Pinned vLLM version:** `0.26.0` (GitHub release 2026-07-27).
Harness constant: `fundamentals/experiments/vllm_load.py::PINNED_VLLM_VERSION`.
Config: `configs/models/phase3.yaml` → `vllm_version: "0.26.0"`.

## Install notes (verified)

| Host | Install |
| --- | --- |
| Linux with CUDA 13 runtime | `pip install vllm==0.26.0` (or matching wheel). Not declared in `pyproject.toml` `gpu` group — that pin conflicts with this repo’s cu124 torch index on laptop resolve. |
| Colab / Kaggle **T4** (typical CUDA **12.x** driver) | Install release asset `vllm-0.26.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl` from the [v0.26.0 release](https://github.com/vllm-project/vllm/releases/tag/v0.26.0). Default CUDA 13 wheels fail with missing `libcudart.so.13`. |
| Native Windows | Not supported; use WSL2 / Colab / Kaggle |

Smoke: `scripts/verify_wsl_vllm.py` (prints `vllm.__version__`).

| Area | Upstream path (tag `v0.26.0`) | Atlas note |
| --- | --- | --- |
| KV / blocks + APC | `vllm/v1/core/kv_cache_manager.py`; design: `docs/design/prefix_caching.md` | Compare Phase 2 block table + whole-prefix hash vs **full-block** hash chains + LRU free queue |
| Scheduler | `vllm/v1/core/sched/scheduler.py` (`schedule()` → `{req_id: num_tokens}`) | Compare toy one-token-per-tick vs token-budget / chunked prefill / preemption |
| Prefix caching | Same KV manager + design doc (hash = parent + block tokens + extras; only full blocks) | Toy keys entire 23-token prefix once — **not** block-aligned APC |
| OpenAI API server | docs: OpenAI-compatible server | Phase 4 worker client must use this pin |

Log file:line references in `docs/phases/phase-3/02_source_diff.md` when reconciling.
