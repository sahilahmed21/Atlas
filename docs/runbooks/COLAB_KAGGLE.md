# Runbook — Colab / Kaggle

Uses **uv** for Phase 1–2 deps. Phase 3 vLLM is installed **separately** (pin `0.26.0`).

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

## Disconnect survival

- CSV appends after every concurrency step.  
- Prefer Drive mount or frequent download on Colab.
