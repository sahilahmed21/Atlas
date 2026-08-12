# Atlas session handoff

**Date:** 2026-08-12 (Phase 7: dual-vLLM infra PASS on Colab; live matrix still pending)  
**Branch:** `master` (local **ahead of origin** — live harness commits not on GitHub until push)  
**Runtime tip (platform):** `ea84aa0` — Phase 5.5 dashboard  
**Harness tip (Phase 7 live CLI):** `517a309` / docs `b4305ee`  
**Next:** Push ≥ `517a309` → Colab pull → re-run live matrix → `SURPRISE_GPU.md`  
**Start:** `docs/phases/phase-7/START_HERE.md` · **Log:** `docs/phases/phase-7/RUN_LOG.md` · Notebook: `docs/runbooks/atlasP5live.ipynb`  
**Repo:** `C:/projects/Atlas`

Paste this file (or `@docs/HANDOFF.md`) into a new chat to resume without rediscovery.

---

## 1. What Atlas is

Research/systems project: demonstrate **production-grade multi-tenant LLM serving behavior** (OpenAI-compatible API, cache-aware routing, real metrics) on **constrained free-path hardware only** (laptop RTX 3050 4GB + Colab/Kaggle T4).

**Not:** “I deployed vLLM on Kubernetes” or faked multi-node / RDMA.

**Constraint (non-negotiable):** multi-replica = time-sliced processes or sequential runs; disaggregation is **informed future work**, not faked.

**Career framing:** Phases 0–6 = free-path MVP. Phases 7–9 = hire-signal arc. Do not market as 30 LPA outshiner until Phase 7 + 9 artifacts exist.

Framing: `docs/framing/ONE_SENTENCE.md` · Root: `README.md` · Pitch: `docs/pitch/ONE_PARAGRAPH.md` · Deep dive: `docs/architecture/PROJECT_DEEP_DIVE.md`

---

## 2. Progress snapshot

| Phase | Status | Eye-stopper / artifact |
| --- | --- | --- |
| 0–6 | **Done** | See prior handoffs / pitch |
| 5 | **Done (sim)** | `results/phase5/` + SURPRISE |
| 5.5 | **Done (UI)** | `/dashboard/` — video → Phase 9 |
| 7 | **In progress** | Infra PASS; **no** live CSV yet |
| 8–10 | Planned | After Phase 7 ACs |

**Phase 7 code:** live harness on laptop (`517a309`). **Phase 7 GPU matrix:** not landed.

---

## 3. What this session accomplished

### Laptop (earlier)
- Live harness TDD: RED `d8ed511` → GREEN `517a309` → docs `b4305ee`
- `uv run pytest platform workers benchmarks -q` → **53 passed**

### Colab (atlasP5live.ipynb) — recorded in RUN_LOG
- T4 + vLLM **0.26.0** pin OK; torch 2.11.0+cu128
- Dual workers :8001 + :8002, util 0.4, Qwen2.5-0.5B — models + inference **PASS**
- Matrix cell used **old clone** (`origin` ≈ `0c871bf`) → CLI flags ignored → **sim** 12-row CSV under `results/phase5/`
- **Not** valid Phase 7 evidence; `phase5-live/` still empty of CSV

### Explicit non-claims
- Do not cite 147.5 / 297.5 / 95.83% as GPU TTFT from this Colab session
- Do not invent live numbers

---

## 4. Key measured findings (cite these; don’t invent)

### Phase 5 — offline simulated (unchanged)

| Cell | Finding |
| --- | --- |
| high_reuse × prefix_aware | hit% 95.83; skew 1.0; TTFT p50 **297.5** vs RR **147.5** |

**Do not cite as GPU TTFT.**

### Phase 7 — infra only (2026-08-12)

Dual time-sliced vLLM on one T4 serves chat on 8001 and 8002. No live routing TTFT matrix yet.

---

## 5. Honesty rules (do not regress)

Prior rules 1–14 still apply. Add:

15. Colab run on tip **without** `--worker-mode` support is **sim**, even if dual vLLM is up.
16. Gate: `run_routing_matrix.py --help | grep worker-mode` before claiming live.

---

## 6. What to do next — finish Phase 7

1. **Push** local commits ≥ `517a309` to GitHub (Colab clones origin).
2. Colab: `git pull` / checkout; confirm `--help` shows `--worker-mode`.
3. Reconfirm 8001/8002 health.
4. Run live harness → `results/phase5-live/routing_matrix_live.csv` with `worker_mode=live`.
5. Write `SURPRISE_GPU.md`; update claim inventory; tick AC-002–006.

Details: `docs/phases/phase-7/RUN_LOG.md`.

---

## 7. Reproduce commands

```powershell
cd C:\projects\Atlas
uv sync
uv run pytest platform workers benchmarks -q

# sim (Phase 5)
uv run python benchmarks/run_routing_matrix.py

# live (Phase 7) — only after dual vLLM up AND tip ≥ 517a309
uv run python benchmarks/run_routing_matrix.py --worker-mode live `
  --patterns high_reuse --strategies round_robin,prefix_aware --n 24 `
  --hardware colab-t4 --vllm-version 0.26.0 --replica-mode time_sliced_dual
```

---

## 8. Preferred working style

Skills: **ponytail**, **karpathy-guidelines**, **tdd-workflow**, **intent-driven-development**.

- PowerShell: `git commit -m "message"` (no bash heredocs)
- Docs-first honesty; no invented GPU metrics

---

## 9. Known gaps / landmines

| Gap | Detail |
| --- | --- |
| Live harness not on origin | Local ahead 3+; Colab will keep getting sim until push+pull |
| No `routing_matrix_live.csv` | AC-002 open |
| Sequential least_load skew | Still a sim/sequential artifact |
| Phase 8–9 | After Phase 7 close |

---

## 10. Quick links

| Need | Path |
| --- | --- |
| Phase 7 run log | `docs/phases/phase-7/RUN_LOG.md` |
| Phase 7 start / ACs | `START_HERE.md` · `ACCEPTANCE.md` |
| Colab notebook | `docs/runbooks/atlasP5live.ipynb` |
| Hire-signal arc | `docs/phases/NEXT_ARC.md` |
| Phase 5 surprise (sim) | `results/phase5/SURPRISE.md` |
| Claim inventory | `docs/phases/phase-6/CLAIM_INVENTORY.md` |
