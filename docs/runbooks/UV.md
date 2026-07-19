# Tooling — uv

Atlas uses [uv](https://docs.astral.sh/uv/) for Python versions, venvs, installs, and script runs. Do not use bare `pip` / `python -m venv` in docs or runbooks.

## Install uv (once per machine)

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Everyday commands

```powershell
cd c:\projects\Atlas

# Create .venv + install project deps (Phase 1–2 default)
uv sync

# Run anything inside the project env (no manual activate required)
uv run python -c "import torch; print(torch.__version__)"
uv run python fundamentals/experiments/naive_hf_load.py

# Add a dependency (updates pyproject.toml + lockfile)
uv add httpx
uv add --group gpu prometheus-client

# Phase 3+ on a CUDA machine / Colab with uv available
uv sync --group gpu
```

## Dependency layout

| Where | What |
| --- | --- |
| `[project].dependencies` | Local Phase 1–2 stack (torch, transformers, …) |
| `[dependency-groups].dev` | Reserved for lint/test |
| `[dependency-groups].gpu` | vLLM + serving clients (Colab/Kaggle) |

Lockfile: `uv.lock` (commit it). Env: `.venv/` (gitignored; created by `uv sync`).

## Colab / Kaggle

If the runtime has no uv yet:

```bash
pip install uv
uv sync --group gpu
```

Or follow current vLLM CUDA install notes, then `uv add --group gpu <package>` so the lockfile stays source of truth.
