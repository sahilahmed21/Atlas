# Runbook — Colab / Kaggle

Uses **uv** for Phase 1–2 deps. Phase 3/7 vLLM is installed **separately** (pin `0.26.0`).

1. Runtime → GPU (T4).  
2. Clone or upload this repo.  
3. Bootstrap Phase 1–2 deps if needed: `pip install uv && uv sync`  
4. Install **pinned** vLLM 0.26.0:
   - **T4 / CUDA 12.x drivers** (typical Colab/Kaggle):
     ```bash
     pip install https://github.com/vllm-project/vllm/releases/download/v0.26.0/vllm-0.26.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
     ```
   - Linux with CUDA 13 runtime: `pip install vllm==0.26.0`  
   - Do **not** use `uv sync --group gpu` — that group is empty (vLLM pin conflicts with this repo’s cu124 torch index on laptop resolve).  
5. `python scripts/verify_wsl_vllm.py` — must print pin ok for `0.26.0`.  
6. Set `hardware_label: colab-t4` in `configs/models/phase3.yaml`.  
7. Run `python fundamentals/experiments/vllm_load.py` then `plot_naive_vs_vllm.py`.  
8. Download `results/phase3/` before the session dies.

## Phase 7 live routing (dual vLLM)

Notebook: `docs/runbooks/atlasP5live.ipynb` · Log: `docs/phases/phase-7/RUN_LOG.md`

1. **Git tip ≥ `517a309`** (live harness). After clone: `git log -1 --oneline` and  
   `uv run python benchmarks/run_routing_matrix.py --help | grep worker-mode`  
   If grep is empty → **STOP** (old tip silently runs Phase 5 sim).
2. Start two servers, util ≈0.4 each, ports 8001/8002, model `Qwen/Qwen2.5-0.5B-Instruct`.
3. Smoke `/v1/models` + one chat each.
4. Run `--worker-mode live` → expect `results/phase5-live/routing_matrix_live.csv` with `worker_mode=live`.

## Disconnect survival

- CSV appends after every concurrency step (Phase 3).  
- Prefer Drive mount or frequent download on Colab.
