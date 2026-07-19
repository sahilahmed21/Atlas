# Runbook — Colab / Kaggle

Uses **uv** for deps (same lockfile as local). Cheat sheet: [`UV.md`](UV.md).

1. Runtime → GPU (T4).  
2. Clone or upload this repo (GitHub recommended once pushed).  
3. Bootstrap uv if missing, then sync the GPU group:
   ```bash
   pip install uv   # bootstrap only — then uv owns the rest
   uv sync --group gpu
   ```
   If vLLM needs a CUDA-specific wheel, follow current vLLM docs then `uv add --group gpu <pin>` so `uv.lock` stays canonical.  
4. Set `hardware_label: colab-t4` in phase config.  
5. Run with `uv run …`.  
6. Save CSV downloads into `results/phaseN/` in the repo before the session dies.

## Disconnect survival

- Write CSV after every sweep step, not only at the end.  
- Prefer Drive mount or frequent download on Colab.
