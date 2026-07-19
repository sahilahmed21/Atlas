# Phase 3 — Real vLLM + source reconciliation

**Hardware:** Colab / Kaggle T4  
**Eye-stopper:** Naive (Phase 1) and vLLM numbers on **one** chart

## Steps

### 3.1 Same load shape as Phase 1
- [ ] Same model family if VRAM allows; else document downsize + why
- [ ] Same concurrency / seq sweep philosophy
- [ ] Save `results/phase3/vllm_load.csv`

### 3.2 Before/after chart
- [ ] Overlay Phase 1 + Phase 3
- [ ] `results/phase3/naive_vs_vllm.png`
- [ ] Caption in `docs/phases/phase-3/01_before_after.md`

### 3.3 Source reconciliation
- [ ] Read vLLM scheduler + block manager (pinned version)
- [ ] Diff concepts vs your toys: `docs/phases/phase-3/02_source_diff.md`
- [ ] List 3 similarities, 3 differences, 1 thing your toy got wrong

### 3.4 Notebook
- [ ] `notebooks/colab/phase3_vllm.ipynb` (create when executing)
