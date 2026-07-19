# Phase 0 — Setup + headline framing

**Status:** Done (skeleton)
**Hardware:** Laptop
**Exit criteria:** Framing locked, repo layout stable, env instructions written

## Steps

### 0.1 Lock framing
- [x] Write [`docs/framing/ONE_SENTENCE.md`](../../framing/ONE_SENTENCE.md)
- [x] Mirror sentence in root README

### 0.2 Repo skeleton
- [x] `/fundamentals` + `/platform` + `/workers` + `/benchmarks` + `/docs`
- [x] `results/` placeholders with `.gitkeep`
- [x] Docs library for phases / knowledge / research

### 0.3 Environment (you do next)
- [ ] Install [uv](https://docs.astral.sh/uv/) (`docs/runbooks/UV.md`)
- [ ] `uv sync` (Python from `.python-version`, env in `.venv`)
- [ ] Confirm laptop CUDA / Torch sees 3050 (or CPU-only for Phase 1 math): `uv run python -c "import torch; print(torch.cuda.is_available())"`
- [ ] Create Colab + Kaggle accounts; bookmark a blank GPU notebook
- [ ] Copy `notebooks/colab/README.md` checklist into first Colab

### 0.4 Tooling
- [ ] `uv sync` locally (Phase 1–2 deps from `pyproject.toml`)
- [ ] Optional: `uv sync --group gpu` only on Colab/Kaggle

## Substeps log

| Date | Note |
| --- | --- |
| 2026-07-19 | Skeleton + docs library created |

## Context for later agents

Phase 0 does not produce charts. Do not start Phase 2 toys until Phase 1 has a measured failure curve saved under `results/phase1/`.
