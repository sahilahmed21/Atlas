# Atlas

**One-sentence framing:** production-grade multi-tenant LLM serving behavior on constrained hardware (laptop 3050 + free-tier T4), without assuming multi-node / RDMA infrastructure.

Atlas is a research-grade ML systems platform: OpenAI-compatible APIs and intelligent routing on top of real measured serving behavior — not "I deployed vLLM on Kubernetes."

## Constraint (non-negotiable)

| Reality | Implication |
| --- | --- |
| Free path only (Colab/Kaggle T4 + laptop 3050) | Multi-replica = time-sliced processes or sequential runs |
| Single consumer GPU | Disaggregation / RDMA is future work, not faked |
| Eye-stoppers must be real | Phase 1 failure curve, Phase 3 before/after, Phase 5.5 live dashboard |

## Repo map

```
fundamentals/   # Phase 1–2: memory math, toy allocators/schedulers/caches
platform/       # Phase 4+: gateway, tenant, router, registry, observability
workers/        # vLLM wrappers, health — workers know nothing about tenants
benchmarks/     # load tests, compare HF vs vLLM, routing experiments
dashboard/      # Phase 5.5 live view
notebooks/      # Colab / Kaggle / local notebooks
configs/        # models, tenants, routing strategies
results/        # measured numbers (CSV/JSON); charts live under docs/experiments
deploy/         # Helm/K8s — grows in Phase 4+, empty until needed
docs/           # every phase, knowledge, research, ADRs, pitch
scripts/        # one-shot runners
```

MVP lives under `fundamentals/` + thin `platform/gateway`. Final architecture fills `platform/`, `workers/`, `deploy/` without reshuffling.

**Architecture diagrams:** [MVP](docs/architecture/MVP_ARCHITECTURE.md) · [Target / production](docs/architecture/TARGET_ARCHITECTURE.md)

## Phases

| Phase | Goal | Eye-stopper |
| --- | --- | --- |
| 0 | Setup + framing | Framing sentence locked |
| 1 | Memory math + naive HF baseline | OOM / latency-collapse curve |
| 2 | Toy paged allocator, continuous batch, prefix cache | Each mechanism tied to Phase 1 failure |
| 3 | Real vLLM + source reconciliation | Naive vs vLLM on one chart |
| 4 | Platform layer; router as centerpiece | Prefix-aware router vs round robin |
| 5 | Routing experiment (find where smart loses) | Surprising underperformance case |
| 5.5 | Live dashboard + 90s demo | Real-time route/cache/TTFT view |
| 6 | Honest write-up + pitch | Constraint → future work coherent |

Details: [`docs/phases/`](docs/phases/) · Start Phase 1: [`docs/phases/phase-1/START_HERE.md`](docs/phases/phase-1/START_HERE.md)

## Hardware (₹0)

| Phase | Hardware |
| --- | --- |
| 0, 1, 2 | Laptop (3050 + CPU) |
| 3 | Colab / Kaggle T4 |
| 4 | Laptop + Colab for GPU tests |
| 5, 5.5 | Colab / Kaggle T4, time-sliced replicas |
| 6 | Laptop |

## Quick start (Phase 0 done → Phase 1)

Requires [uv](https://docs.astral.sh/uv/). See [`docs/runbooks/UV.md`](docs/runbooks/UV.md).

```powershell
cd c:\projects\Atlas
uv sync
uv run python -c "import torch; print(torch.__version__)"

# follow Phase 1
# docs/phases/phase-1/START_HERE.md
```

Phase 3+ GPU stack: `uv sync --group gpu`
## Status

- [x] Phase 0 skeleton + docs library
- [x] Phase 1 memory math + naive baseline
- [ ] Phase 2 toy mechanisms
- [ ] Phase 3 vLLM reconciliation
- [ ] Phase 4 platform + router
- [ ] Phase 5 routing experiment
- [ ] Phase 5.5 live dashboard
- [ ] Phase 6 write-up
