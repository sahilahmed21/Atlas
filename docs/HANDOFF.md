# Atlas session handoff

**Date:** 2026-08-12 (**Phase 7–8 Done** — live WEAKENED + sim load gate)  
**Branch:** `master`  
**Phase 8 tip:** pending commit · gate + `results/phase8/`  
**Next phase:** **Phase 9** — shock package (demo + public README)  
**Start:** `docs/phases/phase-9/README.md` · Arc: `docs/phases/NEXT_ARC.md`  
**Repo:** `C:/projects/Atlas`

Paste this file (or `@docs/HANDOFF.md`) into a new chat to resume without rediscovery.

---

## 1. What Atlas is

Research/systems project: demonstrate **production-grade multi-tenant LLM serving behavior** on **constrained free-path hardware only** (laptop RTX 3050 4GB + Colab/Kaggle T4).

**Not:** multi-node / RDMA / DistServe as implemented.

**Career framing:** Phases 0–8 done on free path (Phase 8 sim gate closed). Hire-signal spike needs Phase 9 (demo/public). Phase 7 **weakens** the dramatic sim story; Phase 8 shows the industry-shaped fix recovers sim sticky TTFT.

Framing: `docs/framing/ONE_SENTENCE.md` · Pitch: `docs/pitch/ONE_PARAGRAPH.md` · Deep dive: `docs/architecture/PROJECT_DEEP_DIVE.md`

---

## 2. Progress snapshot

| Phase | Status | Eye-stopper |
| --- | --- | --- |
| 0–6 | **Done** | Pitch + inventory + platform |
| 5 | **Done (sim)** | ~2× sticky loss (simulated) |
| 5.5 | **Done (UI)** | `/dashboard/` — video → Phase 9 |
| **7** | **Done (live)** | Dual vLLM T4; WEAKENED ~1.17× p50 |
| **8** | **Done (sim)** | Gate: sticky 297.5 → gated 147.5 p50 |
| 9 | **Do next** | Demo + public package |
| 10 | Optional | One JD widener after 9 |

---

## 3. What Phase 7 achieved

- Dual **time_sliced_dual** vLLM **0.26.0** on Colab T4 behind Atlas gateway (`worker_mode=live`)
- high_reuse × RR vs prefix_aware, **n=24**
- Affinity works: hit% **95.83**, skew **1.0** (same pattern as sim)
- Sticky still slower: p50 **33.32** vs RR **28.56** (~**1.17×**); p95 ~**1.23×** — **not** sim’s ~2×
- Verdict **WEAKENED**; claim inventory + ACCEPTANCE AC-001–006 closed
- Early bad Colab run (sim CSV into `results/phase5/`) explicitly **forbidden** as Phase 7 evidence

Tests last known: `uv run pytest platform workers benchmarks -q` → **53 passed**

---

## 4. Key measured findings (cite these; don’t invent)

### Phase 1 — 3050 HF
N=8 p50 **9242 ms** ≈ **5.5×** N=1 — `results/phase1/`

### Phase 3 — T4 vLLM
Batch wall ~210–266 ms; overlay **cross-hardware** — `results/phase3/`

### Phase 5 — sim only
high_reuse prefix p50 **297.5** vs RR **147.5** (~2×) — **not GPU TTFT**

### Phase 7 — live streaming TTFT (Colab T4, dual vLLM)

| Metric | round_robin | prefix_aware |
| --- | ---: | ---: |
| TTFT p50 (ms) | **28.557** | 33.320 (~1.17×) |
| TTFT p95 (ms) | **36.400** | 44.787 (~1.23×) |
| cache hit % | 0 | **95.83** |
| skew | 0.5 | **1.0** |

Data: `results/phase5-live/` · **WEAKENED** vs sim magnitude.

---

## 5. Honesty rules (do not regress)

Prior 1–14 plus:

15. Tip without `--worker-mode` → sim, even if dual vLLM is up.  
16. Confirm `run_routing_matrix.py --help | grep worker-mode` before live claims.  
17. Do **not** say “confirmed 2× GPU penalty” — say **WEAKENED** (~1.17×).  
18. Phase 7 streaming TTFT ≠ Phase 3 batch wall.  
19. Router `cache_signal` ≠ vLLM APC.

---

## 6. What to do next — Phase 8

**Spec:** `docs/phases/phase-8/README.md` · `ACCEPTANCE.md`

Ship minimal prefix-aware **load gate**; before/after table RR vs sticky vs gated on high_reuse (sim required; live preferred). Gate still motivated by live sticky penalty + production failure mode — **not** by a dramatic 2× GPU cliff.

Then Phase 9 (demo citing WEAKENED honestly).

---

## 7. Reproduce

```powershell
cd C:\projects\Atlas
uv sync
uv run pytest platform workers benchmarks -q

# Phase 5 sim
uv run python benchmarks/run_routing_matrix.py

# Phase 7 live (dual vLLM on :8001/:8002)
uv run python benchmarks/run_routing_matrix.py --worker-mode live `
  --patterns high_reuse --strategies round_robin,prefix_aware --n 24 `
  --hardware colab-t4 --vllm-version 0.26.0 --replica-mode time_sliced_dual
```

---

## 8. Prompt starter

```text
Continue Atlas from @docs/HANDOFF.md and @docs/phases/NEXT_ARC.md.

Phase 7 Done (WEAKENED): live dual-vLLM high_reuse — affinity works,
~1.17× sticky p50 vs RR (not sim 2×). Artifacts in results/phase5-live/.
Start Phase 8 per docs/phases/phase-8/README.md: TTFT/load gate +
before/after matrix. Respect honesty; no DistServe; no “confirmed 2×”.
```

---

## 9. Quick links

| Need | Path |
| --- | --- |
| Live surprise | `results/phase5-live/SURPRISE_GPU.md` |
| Live CSV | `results/phase5-live/routing_matrix_live.csv` |
| Phase 7 ACs / RUN_LOG | `docs/phases/phase-7/` |
| Phase 8 start | `docs/phases/phase-8/README.md` |
| Claim inventory | `docs/phases/phase-6/CLAIM_INVENTORY.md` |
| Hire-signal arc | `docs/phases/NEXT_ARC.md` |
| Deep dive | `docs/architecture/PROJECT_DEEP_DIVE.md` |
