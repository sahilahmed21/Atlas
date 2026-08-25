# Atlas

**Multi-tenant LLM inference control plane on free-path GPUs** — an OpenAI-compatible gateway with cache-aware routing, measured end-to-end on a laptop RTX 3050 (4 GiB) and Colab T4. Not a Kubernetes / multi-node / RDMA claim.

[Demo video](docs/demo/atlas-demo.mp4) · [Measured results](results/) · [Architecture](docs/architecture/MVP_ARCHITECTURE.md) · [What shipped](docs/GOALS_AND_SUCCESS.md)

---

## At a glance

| | |
| --- | --- |
| **What it is** | FastAPI OpenAI-compatible API → tenant auth + RPM → routing → vLLM/stub workers → Prometheus + live dashboard |
| **What we measured** | Naive HF latency cliff; vLLM reconciliation; where sticky prefix routing loses; live dual-vLLM validation; load-gate behavior |
| **Hardware** | ₹0 path: RTX 3050 4 GiB + Colab/Kaggle T4 (time-sliced dual replicas) |
| **Stack** | Python 3.11+, FastAPI, httpx, Prometheus, SSE dashboard, vLLM 0.26.0 (Colab) |
| **Honesty** | Simulation ≠ GPU. Router affinity ≠ engine APC. Process-local RPM/events. No DistServe/RDMA theater. |

```text
Client ──► Gateway (auth · RPM · route) ──► Worker A / Worker B (OpenAI HTTP)
                │
                └── observe_request ──► Prometheus + SSE event ring ──► /dashboard/
```

---

## Demo (90s)

Watch: **[docs/demo/atlas-demo.mp4](docs/demo/atlas-demo.mp4)**

What the recording shows: live request feed (worker, cache signal, route reason, TTFT), sticky prefix affinity, then load-gate breaking stickiness — with the free-path honesty constraint stated up front.

---

## Quick start (laptop, no GPU)

Requires [uv](https://docs.astral.sh/uv/).

```powershell
cd C:\projects\Atlas
uv sync
```

**1. Two stub workers** (OpenAI-compatible stand-ins on `:8001` / `:8002` — see [docs/phases/phase-5.5/DEMO.md](docs/phases/phase-5.5/DEMO.md) for the pasteable stubs), matching `configs/models/workers.yaml`.

**2. Gateway** — `PYTHONPATH` is required (`package = false` layout):

```powershell
$env:PYTHONPATH = @(
  "platform\gateway", "platform\tenant", "platform\registry",
  "platform\router", "platform\observability", "workers"
) -join ";"
$env:ATLAS_STRATEGY = "prefix_aware"
$env:ATLAS_PREFIX_LOAD_MARGIN = "0"   # sticky; set "1" to enable load gate
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080
```

**3. Dashboard:** open http://127.0.0.1:8080/dashboard/ · Connect with `sk-atlas-demo-key` (demo key in `configs/tenants/example.yaml`).

**4. Drive load** (shared system prompt / high reuse):

```powershell
$env:PYTHONPATH = "benchmarks;$env:PYTHONPATH"
uv run python benchmarks/demo_load.py
# or: uv run python benchmarks/run_routing_matrix.py --n 24
```

**Health:** `GET /healthz` · **Metrics:** `GET /metrics` (Bearer) · **Events:** `GET /atlas/events?api_key=sk-atlas-demo-key`

Live GPU path (Colab dual vLLM): [docs/runbooks/COLAB_KAGGLE.md](docs/runbooks/COLAB_KAGGLE.md) · Phase 7 notes under `docs/phases/phase-7/`.

---

## Proof of results (open the files)

| Finding | Evidence |
| --- | --- |
| **Naive HF cliff** — Qwen2.5-0.5B on RTX 3050: N=8 p50 **9242 ms** ≈ **5.5×** N=1 (**1671 ms**); peak VRAM ~1.04 GiB (torch) | [results/phase1/](results/phase1/) |
| **vLLM on T4** — pin **0.26.0**; batch wall ~210–266 ms N=1..8; ~15 GB NVML (KV prealloc). Overlay vs Phase 1 is **cross-hardware** | [results/phase3/](results/phase3/) |
| **Sim surprise** — high_reuse sticky routing: hit% **95.8**, skew **1.0**, TTFT p50 **2×** worse than round-robin (`worker_mode=simulated`) | [results/phase5/SURPRISE.md](results/phase5/SURPRISE.md) |
| **Live dual vLLM** — same affinity pattern; sticky ~**1.17×** p50 vs RR → verdict **WEAKENED** (not a confirmed 2× GPU cliff) | [results/phase5-live/SURPRISE_GPU.md](results/phase5-live/SURPRISE_GPU.md) |
| **Load gate** — sim recovers sticky cliff to RR-class; live confirms break mechanics (`hit_broken` 50%, skew 0.5); **live TTFT win vs sticky not claimed** that run | [results/phase8/BEFORE_AFTER.md](results/phase8/BEFORE_AFTER.md) |

Claim rules: [docs/phases/phase-6/CLAIM_INVENTORY.md](docs/phases/phase-6/CLAIM_INVENTORY.md)

---

## What shipped

| Layer | Contents |
| --- | --- |
| **Fundamentals** | Memory/concurrency baseline, CPU toys for paging / continuous batch / prefix hash |
| **Platform** | Gateway, YAML tenants, process-local RPM, RR / least-load / prefix-aware (+ load gate), worker registry |
| **Workers** | Thin OpenAI HTTP client; vLLM pin helper |
| **Benchmarks** | Frozen traffic traces, sim + live routing matrices |
| **Observability** | Prometheus + request-path event ring + `/dashboard/` |
| **Docs** | Phase ACs, runbooks, architecture diagrams, success criteria |

Status checklist and phase index: [docs/phases/README.md](docs/phases/README.md) · Success write-up: [docs/GOALS_AND_SUCCESS.md](docs/GOALS_AND_SUCCESS.md)

---

## Repository layout

```text
fundamentals/   # Phase 1–2 experiments + CPU sims
platform/       # gateway, tenant, router, registry, observability
workers/        # OpenAI worker client (no tenant logic)
benchmarks/     # routing matrix + demo load
dashboard/      # static live UI
configs/        # tenants, workers, models
results/        # CSV / charts / SURPRISE write-ups  ← proof
docs/           # architecture, phases, runbooks
docs/demo/      # demo recording
```

---

## Tests

```powershell
uv run pytest platform workers benchmarks -q
```

---

## Non-goals (explicit)

- Multi-region / RDMA / DistServe-as-implemented  
- Claiming router `cache_signal` as vLLM automatic prefix-cache hit rate  
- Multi-replica-safe RPM or event bus (labeled **process-local**)  
- KEDA / Helm as a live cluster (planning sketches only)

---

## License / key

Demo API key in-repo is synthetic (`sk-atlas-demo-key`). Do not use it outside local demos.
