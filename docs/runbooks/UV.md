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
```

## Dependency layout

| Where | What |
| --- | --- |
| `[project].dependencies` | Local Phase 1–2 stack (torch, transformers, …) |
| `[dependency-groups].dev` | pytest |
| `[dependency-groups].gpu` | **Empty on purpose** — do not `uv sync --group gpu` for vLLM |

Lockfile: `uv.lock` (commit it). Env: `.venv/` (gitignored; created by `uv sync`).

## Colab / Kaggle (Phase 3 vLLM)

Pin is `0.26.0` (`PINNED_VLLM_VERSION`). Install the wheel, then verify:

```bash
pip install uv && uv sync
# T4 / CUDA 12.x:
pip install https://github.com/vllm-project/vllm/releases/download/v0.26.0/vllm-0.26.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
python scripts/verify_wsl_vllm.py
```

See [`COLAB_KAGGLE.md`](COLAB_KAGGLE.md) and `docs/knowledge/vllm-internals/READING_LIST.md`.
