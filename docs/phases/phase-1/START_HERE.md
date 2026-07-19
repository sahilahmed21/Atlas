# Phase 1 — START HERE

**Goal:** Hand-derive KV-cache memory math for a real model, then run naive HuggingFace `generate()` under concurrent load until it breaks — and **plot your hardware's failure curve**.

**Hardware:** Laptop 3050 first (small model / short seq). Optional Colab T4 if laptop OOMs too early to get a useful curve.
**Eye-stopper:** `results/phase1/oom_latency_curve.png` (or SVG) with *your* numbers.

---

## Acceptance (Quick Capture)

**In scope:** Memory formula derivation; concurrent naive HF load; plot of OOM / latency collapse; notes tying failure to math.  
**Out of scope:** vLLM, routers, multi-tenant API, toy paged allocator (that's Phase 2).

### AC-001: Memory formula documented
- **Scenario:** Chosen model (e.g. TinyLlama-1.1B or Qwen2-0.5B / 1.5B for laptop)
- **Action:** Fill `docs/phases/phase-1/01_memory_math.md` tables for ≥3 (batch, seq_len) combos
- **Expected:** Each row shows estimated KV bytes + weights + activations estimate; marks "fits / marginal / OOM"
- **Must not:** Copy a blog formula without plugging *your* dims
- **Verification:** Peer can recompute one row from your formula alone
- **Priority:** Required

### AC-002: Naive concurrent baseline runs
- **Scenario:** Same model, `transformers` generate, N concurrent clients (threads or asyncio)
- **Action:** Run `fundamentals/experiments/naive_hf_load.py` (create in this phase) across a sweep of N and/or max_new_tokens
- **Expected:** CSV in `results/phase1/naive_load.csv` with columns: `n_concurrent, seq_len, max_new_tokens, ttft_ms, tokens_per_s, peak_vram_mb, status`
- **Must not:** Silently catch OOM and continue without recording `status=oom`
- **Verification:** At least one row with `status=oom` or documented latency cliff (>5× median)
- **Priority:** Required

### AC-003: Eye-stopper chart
- **Scenario:** CSV from AC-002 exists
- **Action:** Plot concurrency (or seq) vs latency and mark OOM / collapse
- **Expected:** Chart + caption in `docs/phases/phase-1/03_failure_curve.md` and file under `results/phase1/`
- **Must not:** Textbook diagram without your data points
- **Verification:** Open chart; points match CSV
- **Priority:** Required

### AC-004: Failure modes named for Phase 2
- **Scenario:** Math + curve done
- **Action:** Write `docs/phases/phase-1/04_failure_modes.md` listing exact failures Phase 2 toys must address
- **Expected:** ≥3 named modes (e.g. contiguous KV waste, no continuous batching, no prefix reuse)
- **Priority:** Required

---

## Ordered work (do in order)

1. Read [`01_memory_math.md`](01_memory_math.md) — fill formulas  
   → verify: table complete for 3 combos
2. Pick model + pin revision in [`configs/models/phase1.yaml`](../../../configs/models/phase1.yaml)
3. Implement load script under `fundamentals/experiments/`  
   → verify: dry-run N=1 succeeds
4. Sweep load → write CSV  
   → verify: OOM or collapse captured
5. Plot curve → [`03_failure_curve.md`](03_failure_curve.md)
6. Write [`04_failure_modes.md`](04_failure_modes.md)
7. Check off [`CHECKLIST.md`](CHECKLIST.md)

---

## What you need installed (laptop)

```text
torch          # CUDA if 3050 works; CPU ok for tiny models / math-only day
transformers
accelerate
psutil
# optional: pynvml or torch.cuda.mem_get_info for VRAM
matplotlib
pandas
pyyaml
```

Use **uv**: `uv sync` at repo root (deps in `pyproject.toml`). Heavy GPU deps: `uv sync --group gpu` on Colab/Kaggle. See `docs/runbooks/UV.md`.
---

## Context rules

- Log every run in [`RUN_LOG.md`](RUN_LOG.md) (date, commit, model, hardware, command).
- Raw numbers → `results/phase1/` only. Narrative → this folder.
- Do not start Phase 2 until AC-001–004 pass.
