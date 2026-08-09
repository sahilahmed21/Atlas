# Atlas session handoff

**Date:** 2026-08-10 (Phase 5 offline complete)  
**Branch:** `master`  
**HEAD:** *(update after matrix commit)* — Phase 5 routing matrix + control loop  
**Next phase:** **Phase 5.5** — live dashboard (real metrics from Phase 4 `/metrics`; optional Colab behind gateway)  
**Repo:** `C:/projects/Atlas`

Paste this file (or `@docs/HANDOFF.md`) into a new chat to resume without rediscovery.

---

## 1. What Atlas is

Research/systems project: demonstrate **production-grade multi-tenant LLM serving behavior** (OpenAI-compatible API, cache-aware routing, real metrics) on **constrained free-path hardware only** (laptop RTX 3050 4GB + Colab/Kaggle T4).

**Not:** “I deployed vLLM on Kubernetes” or faked multi-node / RDMA.

**Constraint (non-negotiable):** multi-replica = time-sliced processes or sequential runs; disaggregation is Phase 6 future work, not faked.

Framing: `docs/framing/ONE_SENTENCE.md` · Root: `README.md`

---

## 2. Progress snapshot

| Phase | Status | Eye-stopper / artifact |
| --- | --- | --- |
| 0 Setup + framing | **Done** | Framing locked |
| 1 Memory math + naive HF | **Done** | `results/phase1/oom_latency_curve.png` + CSV |
| 2 Toy allocator / scheduler / prefix cache | **Done** | `results/phase2/*.csv` |
| 3 vLLM reconciliation | **Done** | `results/phase3/naive_vs_vllm.png` + `vllm_load.csv` |
| 4 Platform + router | **Done (offline + review fixes)** | Gateway/router/metrics |
| 5 Routing experiment | **Done (offline sim)** | `results/phase5/` + SURPRISE — prefix-aware loses on high_reuse |
| 5.5 Live dashboard | **Do next** | Real metrics only (from Phase 4 `/metrics`) |
| 6 Write-up + pitch | Blocked | Honest constraint → future work |

Phase index: `docs/phases/README.md`.

---

## 3. What recent sessions accomplished

### Phase 5 offline (`6b4bba6` RED → control-loop GREEN → matrix)
- Shared prefix key; miss→least-load claim; gateway `prefix_owners` + `loads` ±1 (stream-safe)
- Harness: `benchmarks/{traffic,fake_worker,run_routing_matrix}.py`
- Matrix: high_reuse prefix-aware **95.8% hits but 2× worse TTFT p50 vs RR** (sticky saturation)
- Evidence: `docs/testing/phase-5.tdd.md` · ACs: `docs/phases/phase-5/ACCEPTANCE.md`

### Phase 4 review fixes (prior)
- RPM lock, client cache, async offload, OTEL stream, 502/auth/400

**Do not force-push.** Push only if the user asks.

### Tests
```powershell
uv run pytest platform workers benchmarks -q   # 46 passed
uv run python benchmarks/run_routing_matrix.py
```

---

## 4. Key measured findings (cite these; don’t invent)

### Phase 1 — laptop RTX 3050, Qwen2.5-0.5B @ `7ae5576`

| N | p50 latency (ms) | vs N=1 | peak VRAM (MB) |
| --- | --- | --- | --- |
| 1 | 1671 | 1.0× | 969.2 |
| 2 | 2614 | 1.6× | 988.3 |
| 4 | 4405 | 2.6× | 1001.8 |
| 8 | 9242 | **5.5× cliff** | 1042.9 |

Data: `results/phase1/naive_load.csv`

### Phase 2 — CPU sims (not GPU truth)

| Toy | Headline | Artifact |
| --- | --- | --- |
| Allocator | Contiguous waste ≫ paged | `results/phase2/allocator.csv` |
| Scheduler | Continuous busy > static | `results/phase2/scheduler.csv` |
| Prefix cache | Shared 7 hits; unique 0 | `results/phase2/prefix_cache.csv` |

### Phase 3 — Colab T4, vLLM **0.26.0+cu129**, same model revision

| N | batch wall (ms) | NVML used (MB) | status |
| --- | --- | --- | --- |
| 1 | 265.9 | 14956.2 | ok |
| 2 | 210.4 | 14956.2 | ok |
| 4 | 215.6 | 14956.2 | ok |
| 8 | 228.7 | 14956.2 | ok |

- Overlay is **cross-hardware** (3050 vs T4)
- Data: `results/phase3/vllm_load.csv`

### Phase 5 — offline simulated workers only

| Cell | Finding |
| --- | --- |
| high_reuse × prefix_aware | hit% 95.83; skew 1.0; TTFT p50 **297.5** vs RR **147.5** |
| Hypothesis | Sticky affinity saturates one replica; hit savings < saturation penalty |

Data: `results/phase5/routing_matrix.csv` · `SURPRISE.md`  
**Do not cite as GPU TTFT.**

---

## 5. Honesty rules (do not regress)

1. Phase 2 sims **≠** Phase 1/3 GPU metrics.
2. No GIL/kernel root-cause without a profiler trace.
3. Toy prefix cache ≠ vLLM block-aligned APC.
4. Phase 3 latency = **batch wall**, not streaming TTFT.
5. Phase 3 VRAM = **NVML used**; Phase 1 = torch peak — different meters.
6. Overlay **cross-hardware** must stay labeled.
7. Never fake Phase 5.5 dashboard metrics.
8. Phase 5 matrix is **`worker_mode=simulated`** — not Colab APC.
9. RPM + `atlas_queue_depth` are **process-local**.
10. RPM charges on **accept** (`try_acquire`), not on upstream success.
11. KEDA YAML under `deploy/keda/` is a **planning sketch**, not a live run.
12. Router `cache_signal` ≠ vLLM automatic prefix cache.

---

## 6. Code map

### Phase 5
| Path | Role |
| --- | --- |
| `platform/router/strategies.py` | `shared_prefix_key`; miss→least-load |
| `platform/gateway/app.py` | owner claim + loads ±1 |
| `benchmarks/traffic.py` | frozen traces |
| `benchmarks/fake_worker.py` | hit/miss + saturation latency |
| `benchmarks/run_routing_matrix.py` | matrix runner |
| `results/phase5/` | CSV + SURPRISE.md |

### Phase 4 (still current)
| Path | Role |
| --- | --- |
| `platform/gateway/app.py` | FastAPI chat + metrics + SSE |
| `platform/observability/*` | Prometheus + OTEL |
| `workers/openai_worker_client.py` | JSON + stream client |

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
uv run python benchmarks/run_routing_matrix.py

# gateway
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080
```

---

## 8. What to do next — Phase 5.5

**Spec:** `docs/phases/phase-5.5/README.md`  
**Goal:** Live dashboard wired to Phase 4 `/metrics` (and route headers) — **no invented numbers**.

Optional (not blocking 5.5): Colab dual-vLLM re-run of high_reuse surprise cell; TTFT load gate.

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
| Phase 5 = simulated only | No live gateway↔vLLM Colab matrix |
| Sequential least_load skew | In-flight loads clear between requests → sticky first worker |
| No TTFT load gate yet | Documented as follow-up after SURPRISE |
| Process-local RPM/queue | Labeled; not multi-replica safe |
| KEDA sketch | Not applied to a cluster |

---

## 11. Prompt starter for the next chat

```text
Continue Atlas from @docs/HANDOFF.md.

Phase 0–5 done offline (Phase 5 matrix + SURPRISE; platform/workers/benchmarks 46 passed).
Start Phase 5.5 per docs/phases/phase-5.5/README.md: live dashboard from real /metrics.
Do not invent metrics. Respect honesty rules (simulated ≠ GPU; process-local RPM).
```

---

## 12. Quick links

| Need | Path |
| --- | --- |
| Phase index | `docs/phases/README.md` |
| Phase 5 ACs | `docs/phases/phase-5/ACCEPTANCE.md` |
| Phase 5 TDD | `docs/testing/phase-5.tdd.md` |
| Matrix | `docs/experiments/routing_matrix.md` |
| Phase 5.5 start | `docs/phases/phase-5.5/README.md` |
| Colab runbook | `docs/runbooks/COLAB_KAGGLE.md` |
| MVP architecture | `docs/architecture/MVP_ARCHITECTURE.md` |
