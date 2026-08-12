# Atlas session handoff

**Date:** 2026-08-12 (Phases 0–6 done; hire-signal arc Phases 7–10 planned)  
**Branch:** `master`  
**Prior feature tip:** `ea84aa0` — `feat: Phase 5.5 live event feed + dashboard (GREEN)`  
**Phase 6:** docs under `docs/phases/phase-6/` + `docs/pitch/` (closed)  
**Next phase:** **Phase 7** — live GPU routing validation (`docs/phases/phase-7/START_HERE.md`)  
**Hire-signal plan:** `docs/phases/NEXT_ARC.md`  
**Repo:** `C:/projects/Atlas`

Paste this file (or `@docs/HANDOFF.md`) into a new chat to resume without rediscovery.

---

## 1. What Atlas is

Research/systems project: demonstrate **production-grade multi-tenant LLM serving behavior** (OpenAI-compatible API, cache-aware routing, real metrics) on **constrained free-path hardware only** (laptop RTX 3050 4GB + Colab/Kaggle T4).

**Not:** “I deployed vLLM on Kubernetes” or faked multi-node / RDMA.

**Constraint (non-negotiable):** multi-replica = time-sliced processes or sequential runs; disaggregation is **informed future work**, not faked.

Framing: `docs/framing/ONE_SENTENCE.md` · Root: `README.md` · Pitch: `docs/pitch/ONE_PARAGRAPH.md`

---

## 2. Progress snapshot

| Phase | Status | Eye-stopper / artifact |
| --- | --- | --- |
| 0 Setup + framing | **Done** | Framing locked |
| 1 Memory math + naive HF | **Done** | `results/phase1/oom_latency_curve.png` + CSV |
| 2 Toy allocator / scheduler / prefix cache | **Done** | `results/phase2/*.csv` |
| 3 vLLM reconciliation | **Done** | `results/phase3/naive_vs_vllm.png` + `vllm_load.csv` |
| 4 Platform + router | **Done (offline)** | Gateway/router/metrics; review hardened |
| 5 Routing experiment | **Done (offline sim)** | `results/phase5/` + SURPRISE — prefix-aware loses on high_reuse |
| 5.5 Live dashboard | **Done (UI; video deferred)** | `/dashboard/` + `/atlas/events` from request path |
| 6 Write-up + pitch | **Done** | Claim inventory + pitch + resume bullets |
| 7 Live GPU routing validation | **Do next** | `results/phase5-live/` + SURPRISE_GPU |
| 8 TTFT / load gate | **Planned** | Before/after RR vs sticky vs gated |
| 9 Shock package | **Planned** | 90s video + public README sell |
| 10 Optional widener | **Optional** | One of RAG / eval / cost after 9 |

Phase index: `docs/phases/README.md` · Arc: `docs/phases/NEXT_ARC.md`.

---

## 3. What recent sessions accomplished

### Phase 6 (docs-only)
- `docs/phases/phase-6/CLAIM_INVENTORY.md` — allowed / forbidden / future
- `docs/phases/phase-6/ACCEPTANCE.md` — AC-001–007
- `docs/phases/phase-6/README.md` — narrative arc (status corrected; prior draft said only Phase 1 existed)
- `docs/pitch/ONE_PARAGRAPH.md` — present-tense, inventory-backed
- `docs/pitch/RESUME_BULLETS.md` — 5 bullets; no DistServe / no “improved X%”
- Root `README.md` — short arc + Phase 6 checked

### Phase 5.5 (prior; still current runtime)
- `RequestEventLog` ring; `observe_request` publishes events (includes route `reason`)
- `GET /atlas/snapshot`, `GET /atlas/events` (SSE); static `dashboard/` at `/dashboard/`
- Auth: Bearer **or** `api_key` query on `/atlas/*` only
- Evidence: `docs/testing/phase-5.5.tdd.md` · **52 passed** last known
- 90s demo **video not recorded** — `docs/phases/phase-5.5/DEMO.md`

### Phase 5 offline (prior)
- high_reuse prefix-aware **95.8% hits but 2× worse TTFT p50 vs RR** (`SURPRISE.md`)

**Do not force-push.** Push only if the user asks.

### Tests
```powershell
uv run pytest platform workers benchmarks -q   # 52 passed last known
uv run python benchmarks/run_routing_matrix.py
```

---

## 4. Key measured findings (cite these; don’t invent)

### Phase 1 — laptop RTX 3050, Qwen2.5-0.5B

| N | p50 latency (ms) | vs N=1 | peak VRAM (MB) |
| --- | --- | --- | --- |
| 1 | 1671 | 1.0× | 969.2 |
| 8 | 9242 | **5.5× cliff** | 1042.9 |

Data: `results/phase1/naive_load.csv`

### Phase 3 — Colab T4, vLLM **0.26.0+cu129**

- Batch wall ~210–266 ms for N=1..8; ~15 GB flat NVML = KV preallocation
- Overlay is **cross-hardware** (3050 vs T4) — keep labeled
- Data: `results/phase3/vllm_load.csv`

### Phase 5 — offline simulated workers only

| Cell | Finding |
| --- | --- |
| high_reuse × prefix_aware | hit% 95.83; skew 1.0; TTFT p50 **297.5** vs RR **147.5** |
| Hypothesis | Sticky affinity saturates one replica; hit savings < saturation penalty |

Data: `results/phase5/routing_matrix.csv` · `SURPRISE.md`  
**Do not cite as GPU TTFT.**

### Phase 5.5

Live UI only — numbers from gateway request-path event ring. No new GPU numbers.

### Phase 6

Docs only — no new metrics. Gate: `docs/phases/phase-6/CLAIM_INVENTORY.md`.

---

## 5. Honesty rules (do not regress)

1. Phase 2 sims **≠** Phase 1/3 GPU metrics.
2. No GIL/kernel root-cause without a profiler trace.
3. Toy prefix cache ≠ vLLM block-aligned APC; router `cache_signal` ≠ engine APC.
4. Phase 3 latency = **batch wall**, not streaming TTFT.
5. Phase 3 VRAM = **NVML used**; Phase 1 = torch peak — different meters.
6. Overlay **cross-hardware** must stay labeled.
7. Phase 5 matrix is **`worker_mode=simulated`** — not Colab APC.
8. Never invent dashboard metrics; never store prompt/user text in events.
9. RPM + `atlas_queue_depth` + event ring are **process-local**.
10. RPM charges on **accept** (`try_acquire`), not on upstream success.
11. KEDA YAML under `deploy/keda/` is a **planning sketch**, not a live run.
12. Demo video link empty until a real recording exists.

---

## 6. Code map

### Phase 5.5
| Path | Role |
| --- | --- |
| `platform/observability/request_events.py` | Bounded event ring |
| `platform/observability/atlas_metrics.py` | observe → Prometheus + events |
| `platform/gateway/app.py` | `/atlas/*` + StaticFiles `/dashboard` |
| `dashboard/index.html` | Live UI |

### Phase 5
| Path | Role |
| --- | --- |
| `platform/router/strategies.py` | `shared_prefix_key`; miss→least-load |
| `benchmarks/{traffic,fake_worker,run_routing_matrix}.py` | Offline matrix |
| `results/phase5/` | CSV + SURPRISE.md |

### Phase 4 (still current)
| Path | Role |
| --- | --- |
| `platform/gateway/app.py` | FastAPI chat + metrics + SSE |
| `platform/tenant/` | YAML tenants + process-local RPM |
| `workers/openai_worker_client.py` | JSON + stream client |

### Phase 6 (docs)
| Path | Role |
| --- | --- |
| `docs/phases/phase-6/CLAIM_INVENTORY.md` | Allowed / forbidden / future |
| `docs/pitch/ONE_PARAGRAPH.md` | Final pitch |
| `docs/pitch/RESUME_BULLETS.md` | Resume bullets |

### Dependency landmine
- `pyproject.toml` `gpu = []` on purpose.
- Colab T4: `+cu129` wheel only.
- Gitignore: **`/models/`** (repo-root).

---

## 7. Reproduce commands

```powershell
cd C:\projects\Atlas
uv sync
uv run pytest platform workers benchmarks -q

# gateway + dashboard
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080
# open http://127.0.0.1:8080/dashboard/
# Connect with sk-atlas-demo-key (configs/tenants/example.yaml)

# Phase 5 matrix (offline)
uv run python benchmarks/run_routing_matrix.py
```

---

## 8. What to do next — Phase 7 (hire-signal arc)

**Master plan:** `docs/phases/NEXT_ARC.md`  
**Start:** `docs/phases/phase-7/START_HERE.md`  
**ACs:** `docs/phases/phase-7/ACCEPTANCE.md`

**Goal:** Re-run high_reuse × {round_robin, prefix_aware} on dual time-sliced vLLM behind the gateway; publish `results/phase5-live/`. Confirm, weaken, or refute the Phase 5 sim — do not force the narrative.

Then: Phase 8 load gate → Phase 9 demo/public package. Phase 10 only after 9.

**Still deferred until Phase 9:** 90s demo video link.

---

## 9. Preferred working style

Skills: **ponytail**, **karpathy-guidelines**, **tdd-workflow**, **intent-driven-development**.

- `uv run` / `uv sync`; Python `>=3.11,<3.14`
- RED → GREEN checkpoint commits when TDD active
- PowerShell: `git commit -m "message"` (no bash heredocs)
- Fewest files; unique test module basenames

---

## 10. Known gaps / landmines

| Gap | Detail |
| --- | --- |
| Phase 5 = simulated only | Phase 7 exists to fix this for the headline cell |
| Phase 5.5 video | Deferred to Phase 9; UI + runbook ready |
| Sequential least_load skew | In-flight loads clear between requests → sticky first worker |
| No TTFT load gate yet | Phase 8 |
| Process-local RPM/queue/events | Labeled; not multi-replica safe |
| KEDA sketch | Not applied to a cluster |
| Public shock package | Phase 9 |

---

## 11. Prompt starter for the next chat

```text
Continue Atlas from @docs/HANDOFF.md and @docs/phases/NEXT_ARC.md.

Phases 0–6 done. Start Phase 7 per docs/phases/phase-7/START_HERE.md:
live dual-vLLM (or sequential-isolated) high_reuse validation behind the
gateway; land results/phase5-live/. Respect honesty rules — confirm or
refute the sim; do not invent metrics or claim DistServe/RDMA.
```

---

## 12. Quick links

| Need | Path |
| --- | --- |
| Hire-signal arc | `docs/phases/NEXT_ARC.md` |
| Phase 7 start / ACs | `docs/phases/phase-7/START_HERE.md` · `ACCEPTANCE.md` |
| Phase 8 / 9 / 10 | `docs/phases/phase-8/` · `phase-9/` · `phase-10/` |
| Phase index | `docs/phases/README.md` |
| Phase 6 claims / ACs | `docs/phases/phase-6/CLAIM_INVENTORY.md` · `ACCEPTANCE.md` |
| Pitch / resume | `docs/pitch/ONE_PARAGRAPH.md` · `RESUME_BULLETS.md` |
| Phase 5 ACs / TDD | `docs/phases/phase-5/ACCEPTANCE.md` · `docs/testing/phase-5.tdd.md` |
| Phase 5.5 ACs / TDD | `docs/phases/phase-5.5/ACCEPTANCE.md` · `docs/testing/phase-5.5.tdd.md` |
| Phase 5.5 demo | `docs/phases/phase-5.5/DEMO.md` |
| Routing matrix | `docs/experiments/routing_matrix.md` |
| Colab runbook | `docs/runbooks/COLAB_KAGGLE.md` |
| Free-path replicas | `docs/knowledge/hardware-constraints/FREE_PATH_REPLICAS.md` |
| Project deep dive | `docs/architecture/PROJECT_DEEP_DIVE.md` |
| MVP architecture | `docs/architecture/MVP_ARCHITECTURE.md` |
