# Runbook — local Phase 1

Uses **uv** only. Full cheat sheet: [`UV.md`](UV.md).

```powershell
cd c:\projects\Atlas
uv sync
```

1. Edit `configs/models/phase1.yaml` if 1.1B won't fit.  
2. Follow `docs/phases/phase-1/START_HERE.md`.  
3. Run scripts with `uv run …` (no manual `activate` needed).  
4. Log every run in `docs/phases/phase-1/RUN_LOG.md`.

## CUDA check

```powershell
uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"
```

If CUDA false: still do memory math + tiny CPU model for protocol; move load sweep to Colab.
