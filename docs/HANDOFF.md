# Atlas session handoff

**Date:** 2026-08-10 (Phase 5.5 live dashboard)  
**Branch:** `master`  
**HEAD:** *(update after GREEN commit)*  
**Next phase:** **Phase 6** — honest write-up + pitch  
**Repo:** `C:/projects/Atlas`

Paste this file (or `@docs/HANDOFF.md`) into a new chat to resume without rediscovery.

---

## 1. What Atlas is

Research/systems project: demonstrate **production-grade multi-tenant LLM serving behavior** (OpenAI-compatible API, cache-aware routing, real metrics) on **constrained free-path hardware only** (laptop RTX 3050 4GB + Colab/Kaggle T4).

**Constraint (non-negotiable):** multi-replica = time-sliced processes or sequential runs; disaggregation is Phase 6 future work, not faked.

Framing: `docs/framing/ONE_SENTENCE.md` · Root: `README.md`

---

## 2. Progress snapshot

| Phase | Status | Eye-stopper / artifact |
| --- | --- | --- |
| 0–4 | **Done** | Framing → platform |
| 5 Routing experiment | **Done (offline sim)** | `results/phase5/SURPRISE.md` |
| 5.5 Live dashboard | **Done (UI; video deferred)** | `/dashboard/` + `/atlas/events` |
| 6 Write-up + pitch | **Do next** | Constraint → future work |

---

## 3. What recent sessions accomplished

### Phase 5.5
- `RequestEventLog` ring; `observe_request` publishes events (includes route `reason`)
- `GET /atlas/snapshot`, `GET /atlas/events` (SSE catch-up + live; `catchup_only` for tests)
- Static `dashboard/index.html` at `/dashboard/` with honesty banner
- Auth: Bearer or `api_key` query on `/atlas/*` only
- **52 passed** (`platform workers benchmarks`)
- Video recording left for human follow-up (`DEMO.md`)

### Phase 5 offline (prior)
- Control loop + matrix; high_reuse prefix-aware loses vs RR on simulated TTFT

### Tests
```powershell
uv run pytest platform workers benchmarks -q
```

---

## 4. Key findings (cite; don’t invent)

- Phase 1 cliff N=8 ≈ 5.5× on 3050 — `results/phase1/`
- Phase 3 Colab T4 vLLM batch wall — `results/phase3/`
- Phase 5 high_reuse: prefix-aware hit% 95.8, TTFT p50 **2× worse** than RR — `results/phase5/`
- Phase 5.5: live events from request path only — not Grafana-invented

---

## 5. Honesty rules

1. Sims ≠ GPU; Phase 5 = `worker_mode=simulated`
2. Router `cache_signal` ≠ vLLM APC
3. RPM / queue / event ring = **process-local**
4. Never invent dashboard metrics
5. Dashboard must not store prompt/user text in events

---

## 6. Code map (5.5)

| Path | Role |
| --- | --- |
| `platform/observability/request_events.py` | Ring buffer |
| `platform/observability/atlas_metrics.py` | observe → Prometheus + events |
| `platform/gateway/app.py` | `/atlas/*` + StaticFiles `/dashboard` |
| `dashboard/index.html` | Live UI |

---

## 7. Reproduce

```powershell
cd C:\projects\Atlas
uv sync
uv run pytest platform workers benchmarks -q
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080
# open http://127.0.0.1:8080/dashboard/
```

---

## 8. Next — Phase 6

Honest write-up + pitch: constraint → measured findings → informed future work (no faked DistServe).  
Optional: record 5.5 demo video; Colab dual-vLLM validation; TTFT load gate.

---

## 11. Prompt starter

```text
Continue Atlas from @docs/HANDOFF.md.

Phases 0–5.5 done (live dashboard UI; video deferred; 52 passed).
Start Phase 6 write-up/pitch per docs/phases (honest constraint → future work).
Do not invent metrics or claim multi-node.
```
