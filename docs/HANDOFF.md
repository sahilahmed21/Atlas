# Atlas session handoff

**Date:** 2026-08-08 (updated after Phase 4 E2E offline)  
**Branch:** `master`  
**HEAD:** see `git log -1` — Phase 4 GREEN after `dcaa927` RED  
**Next phase:** **Phase 5** — routing experiment (find where prefix-aware loses)  
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
| 4 Platform + router | **Done (offline)** | Gateway + router + `/metrics`; `32 passed` |
| 5 Routing experiment | **Do next** | Find where prefix-aware **loses** |
| 5.5 Live dashboard | Blocked on 5 metrics use | Real metrics only |
| 6 Write-up + pitch | Blocked | Honest constraint → future work |

Phase index: `docs/phases/README.md`.

---

## 3. What recent sessions accomplished

### Phase 4 E2E (this session)
- AC-001–013 offline: RPM (process-local labeled), upstream SSE + TTFT timings, Prometheus request-path metrics, OTEL span hook, KEDA sketch, vLLM pin helper
- TDD: RED `dcaa927` → GREEN (see `docs/testing/phase-4.tdd.md`)
- Exa MCP unavailable; verified `/metrics` (`generate_latest`), SSE, KEDA shapes via web search

### Phase 4 scaffold (prior)
- FastAPI gateway, YAML tenant/registry, round_robin / least_load / prefix_aware, fake-worker tests

### Phase 3 (prior)
- Colab T4 vLLM 0.26.0+cu129; `results/phase3/*`; cross-hardware overlay labeled

**Do not force-push.** Push only if the user asks.

### Tests
`uv run pytest platform workers -q` → **32 passed**  
Fundamentals (last known): `25 passed`

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
- ~15 GB flat NVML = vLLM KV **preallocation** on T4
- Data: `results/phase3/vllm_load.csv` · Eye-stopper: `results/phase3/naive_vs_vllm.png`

### Phase 4 — offline only (no new GPU numbers)

Do not invent live TTFT/cache-hit rates. Metrics come from the gateway request path under test.

---

## 5. Honesty rules (do not regress)

1. Phase 2 sims **≠** Phase 1/3 GPU metrics.
2. No GIL/kernel root-cause without a profiler trace.
3. Toy prefix cache ≠ vLLM block-aligned APC.
4. Phase 3 latency = **batch wall**, not streaming TTFT.
5. Phase 3 VRAM = **NVML used**; Phase 1 = torch peak — different meters.
6. Overlay **cross-hardware** must stay labeled.
7. Never fake Phase 5 / 5.5 results or dashboard metrics.
8. RPM + `atlas_queue_depth` are **process-local** (`x-atlas-rpm-scope: process-local`).
9. KEDA YAML under `deploy/keda/` is a **planning sketch**, not a live run.
10. Live Colab worker behind gateway is optional follow-up — not required to have closed Phase 4 offline.

---

## 6. Code map

### Phase 4 (complete offline)
| Path | Role |
| --- | --- |
| `platform/gateway/app.py` | FastAPI chat + RPM + metrics + SSE passthrough |
| `platform/tenant/tenants.py` + `rpm.py` | YAML tenants + process-local RPM |
| `platform/registry/workers_registry.py` | YAML workers |
| `platform/router/strategies.py` | RR / least-load / prefix-aware + `cache_signal` |
| `platform/observability/atlas_metrics.py` | Prometheus request-path metrics |
| `platform/observability/otel_hooks.py` | `atlas.chat_completions` span |
| `workers/openai_worker_client.py` | JSON + stream client + timings |
| `workers/vllm_pin.py` | Pin `0.26.0` |
| `deploy/keda/atlas-queue-depth.yaml` | Planning sketch |
| `docs/phases/phase-4/ACCEPTANCE.md` | AC-001–013 |
| `docs/testing/phase-4.tdd.md` | RED/GREEN evidence |

### Dependency landmine
- `pyproject.toml` `gpu = []` on purpose.
- Colab T4: `+cu129` wheel only.
- Gitignore: **`/models/`** (repo-root).

---

## 7. Reproduce commands

```powershell
cd C:\projects\Atlas
uv sync
uv run pytest platform workers -q
uv run pytest fundamentals/experiments fundamentals/allocators fundamentals/schedulers fundamentals/prefix_cache -q

# gateway (needs worker URLs in configs/models/workers.yaml)
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080
```

---

## 8. What to do next — Phase 5

**Spec:** `docs/phases/phase-5/README.md`  
**Goal:** Find where prefix-aware routing **loses** vs round-robin (surprising underperformance), with inspectable route reasons from Phase 4.

Do not invent metrics. Prefer fake/time-sliced workers on laptop first; Colab when GPU truth is required.

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
| No live gateway↔vLLM Colab run | Offline Phase 4 closed; optional follow-up |
| Process-local RPM/queue | Labeled; not multi-replica safe |
| KEDA sketch | Not applied to a cluster |
| Pitch | May still mix measured + future — keep honest |

---

## 11. Prompt starter for the next chat

```text
Continue Atlas from @docs/HANDOFF.md.

Phase 0–4 done offline (Phase 4: platform workers 32 passed; metrics from
request path; RPM process-local labeled). Start Phase 5 per
docs/phases/phase-5/README.md: find where prefix-aware routing loses vs
round-robin. Use TDD + intent ACs. Do not invent dashboard metrics.
```

---

## 12. Quick links

| Need | Path |
| --- | --- |
| Phase index | `docs/phases/README.md` |
| Phase 4 ACs | `docs/phases/phase-4/ACCEPTANCE.md` |
| Phase 4 TDD | `docs/testing/phase-4.tdd.md` |
| Phase 5 start | `docs/phases/phase-5/README.md` |
| Colab runbook | `docs/runbooks/COLAB_KAGGLE.md` |
| MVP architecture | `docs/architecture/MVP_ARCHITECTURE.md` |
