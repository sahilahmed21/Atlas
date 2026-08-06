# Phase 3 — Before/after chart

**Status: pending GPU run (AC-005).** Overlay plotter and join logic are implemented and unit-tested; measured `results/phase3/vllm_load.csv` and `naive_vs_vllm.png` do not exist until Colab/Kaggle executes the harness.

| Item | Value |
| --- | --- |
| vLLM pin | `0.26.0` (`PINNED_VLLM_VERSION` / `configs/models/phase3.yaml`) |
| Model | `Qwen/Qwen2.5-0.5B-Instruct` @ `7ae5576…` |
| Naive baseline | `results/phase1/naive_load.csv` (laptop-3050) |
| Expected vLLM hardware | `colab-t4` (or Kaggle T4) |
| TTFT | **proxy = batch wall** (`ttft_proxy=batch_wall`); not streaming TTFT |
| VRAM | Phase 3: `vram_source=nvml` (used bytes); Phase 1: torch peak — not identical meters |
| Concurrency | One `LLM.generate([p0..pN-1])` with `[req=i]` suffixes (not threaded singles) |
| Overlay command | `uv run python fundamentals/experiments/plot_naive_vs_vllm.py` (after CSV exists; title labels hardware) |

When the GPU run finishes, embed `results/phase3/naive_vs_vllm.png` here and fill:

- exact installed wheel (`+cu129` vs default) and `vllm.__version__`
- dtype / GPU memory utilization setting if non-default
- which concurrency points were included or cliff-stopped
- whether differences are limited to what measurements + `02_source_diff.md` support
