# Phase 7 — START HERE (live GPU routing validation)

**Status:** Not started  
**Hardware:** Colab/Kaggle T4 — **time-sliced dual vLLM** (or sequential isolated runs if dual concurrent OOM)  
**Eye-stopper:** GPU-backed high_reuse cell in `results/phase5-live/`

## Why this phase exists

Phase 5 proved the surprise **offline** (`worker_mode=simulated`). Interviewers will attack that. Phase 7 makes the headline **indefensible to dismiss as a toy** — or honestly retracts it if GPU reality differs.

## Do in order

1. Read [README.md](README.md) + [ACCEPTANCE.md](ACCEPTANCE.md)
2. Read free-path replica notes: `docs/knowledge/hardware-constraints/FREE_PATH_REPLICAS.md`
3. Read Colab runbook: `docs/runbooks/COLAB_KAGGLE.md` (vLLM **0.26.0** `+cu129`)
4. Wire gateway → two OpenAI-compatible vLLM endpoints (`configs/models/workers.yaml`)
5. Replay **high_reuse** (and RR vs prefix_aware at minimum) through the real gateway
6. Write `results/phase5-live/` CSV + `SURPRISE_GPU.md`
7. Tick ACs in ACCEPTANCE.md

## Non-negotiable

- Label hardware, vLLM version, `gpu_memory_utilization`, concurrent vs sequential replicas
- Never call router `cache_signal` “vLLM APC hit”
- If live result ≠ sim: **publish disagreement** — do not force the narrative

## Next

Phase 8 (TTFT load gate) only after Phase 7 artifacts exist (or explicitly defer live and note gap — weaker hire signal).
