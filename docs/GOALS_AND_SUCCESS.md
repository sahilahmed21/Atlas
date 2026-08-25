# Atlas — goals achieved and why this project is complete

**Audience:** public repo readers and future maintainers.  
**Date:** 2026-08-25  
**Scope:** free-path MVP through Phase 8 + demo recording. Phase 9 packaging is largely met by the root README + demo video; Phase 10 remains optional.

---

## 1. Original intent (constrained)

Demonstrate **production-grade multi-tenant LLM serving behavior** on **₹0 hardware** (laptop RTX 3050 4 GiB + Colab/Kaggle T4):

- OpenAI-compatible API  
- Tenant keys / quotas (simple)  
- Cache-aware routing with a place where “smart” loses  
- Real measured artifacts (CSV / charts / write-ups)  
- **No** faked multi-node, RDMA, or DistServe  

Framing: `docs/framing/ONE_SENTENCE.md`.

---

## 2. Goals → status

| Goal | Status | Proof |
| --- | --- | --- |
| Lock honest free-path constraint | **Done** | Framing + ADRs |
| Measure naive HF failure under concurrency | **Done** | `results/phase1/` — 5.5× p50 cliff |
| Teach paging / batching / prefix via readable toys | **Done** | `fundamentals/` + `results/phase2/` (CPU only) |
| Reconcile with pinned vLLM on T4 | **Done** | `results/phase3/` — cross-hardware overlay labeled |
| Ship gateway + tenancy + routers + metrics | **Done** | `platform/` + tests |
| Find where prefix-aware loses | **Done (sim)** | `results/phase5/SURPRISE.md` — ~2× TTFT vs RR |
| Live dual-vLLM validation | **Done** | `results/phase5-live/` — verdict **WEAKENED** (~1.17×) |
| Load gate (break sticky when hot) | **Done** | `results/phase8/` — sim recover; live mechanics, no live TTFT win claimed |
| Live dashboard from request path | **Done** | `/dashboard/` + `/atlas/events` |
| Demo recording | **Done** | `docs/demo/atlas-demo.mp4` |
| Defensible public claims | **Done** | `docs/phases/phase-6/CLAIM_INVENTORY.md` + root README |
| DistServe / multi-region / Istio | **Out of scope** | Documented as future / non-goals |
| Optional RAG/eval widener | **Optional** | Phase 10 — not required for MVP close |

---

## 3. Definition of “success” for this repo

Atlas is a **success** when all of the following are true:

1. **Constraint held** — no DistServe/RDMA/multi-region claims.  
2. **Eye-stoppers are files** — every headline number opens a CSV or write-up under `results/`.  
3. **Control plane exists** — OpenAI chat path, auth, RPM, three routers + gate, observability.  
4. **Science loop closed** — sim hypothesis → live confirm/weaken → mitigation measured.  
5. **A stranger can run or watch** — README quick start and/or demo video.  
6. **Honesty survives grilling** — sim ≠ GPU; router ≠ APC; process-local labeled.

All six are met as of this document.

---

## 4. Why “complete” does not mean “production cloud platform”

Complete **for the free-path research/demo charter**:

- Process-local RPM and event ring are intentional ceilings.  
- Dual replicas on one T4 are time-sliced, not multi-GPU HA.  
- Live TTFT ranking can vary (Phase 7 vs Phase 8); we published both.  

Incomplete **as a commercial multi-region inference product** — that was never the ₹0 deliverable. See `docs/architecture/TARGET_ARCHITECTURE.md` for the north star, explicitly not claimed as implemented.

---

## 5. Headline outcomes (for README / talks)

1. **Naive serving fails loudly** before VRAM OOMs — 5.5× latency cliff on a 3050.  
2. **vLLM changes the shape** of concurrency (batch wall / KV prealloc) — meters kept distinct.  
3. **Cache-aware routing is not free** — sticky affinity can saturate one replica (sim 2×; live weakened).  
4. **Mitigation is a load gate** — control works; benefit is workload/hardware dependent.  
5. **Measurement > theater** — WEAKENED and “TTFT win not confirmed” are first-class results.

---

## 6. Remaining optional work (not blockers)

- Phase 10: one JD widener (RAG lane / eval harness / cost model)  
- Compose one-command demo / local k3s (ops learning, still single-node)  
- Engine KV-event routing (true APC awareness) — needs more infra  

None of these reopen the MVP success criteria above.

---

## 7. Checklist (maintainers)

- [x] Phases 0–8 evidenced  
- [x] Claim inventory current  
- [x] Root README recruiter-facing  
- [x] Demo video linked  
- [x] Tests: `uv run pytest platform workers benchmarks -q`  
- [ ] Phase 10 only if a specific JD needs it  
