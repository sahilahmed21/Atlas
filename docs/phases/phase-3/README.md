# Phase 3 — Real vLLM + source reconciliation

**Hardware:** Colab / Kaggle T4  
**Eye-stopper:** Naive (Phase 1) and vLLM numbers on **one** chart  
**Acceptance:** [`ACCEPTANCE.md`](ACCEPTANCE.md)  
**Pin:** vLLM **0.26.0** — [`READING_LIST.md`](../../knowledge/vllm-internals/READING_LIST.md)

## Steps

### 3.1 Same load shape as Phase 1
- [x] Config: `configs/models/phase3.yaml` (same model revision + concurrency philosophy)
- [x] Harness: `fundamentals/experiments/vllm_load.py` (offline helpers tested)
- [ ] Save `results/phase3/vllm_load.csv` — **needs Colab/Kaggle**

### 3.2 Before/after chart
- [x] Overlay plotter: `fundamentals/experiments/plot_naive_vs_vllm.py` (unit-tested)
- [ ] `results/phase3/naive_vs_vllm.png` — **needs CSV**
- [x] Caption stub: `01_before_after.md` (fill after GPU run)

### 3.3 Source reconciliation
- [x] Diff vs toys: `02_source_diff.md` (tag `v0.26.0`)

### 3.4 Notebook
- [x] `notebooks/colab/phase3_vllm.ipynb`

## Colab install (T4 / CUDA 12.x drivers)

```python
# Prefer +cu129 wheel — default PyPI 0.26.0 expects CUDA 13 (libcudart.so.13)
!pip install -q https://github.com/vllm-project/vllm/releases/download/v0.26.0/vllm-0.26.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
```

Then clone/upload the repo and run:

```bash
python fundamentals/experiments/vllm_load.py --config configs/models/phase3.yaml
python fundamentals/experiments/plot_naive_vs_vllm.py
```
