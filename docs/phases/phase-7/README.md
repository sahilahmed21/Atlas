# Phase 7 — Live GPU routing validation

**Status:** In progress — dual-vLLM **infra PASS** (2026-08-12); live matrix **blocked** until Colab uses tip ≥ `517a309`  
**Hardware:** Colab/Kaggle T4 — time-sliced dual vLLM preferred  
**Eye-stopper:** `results/phase5-live/` — GPU CSV + `SURPRISE_GPU.md`  
**ACs:** [ACCEPTANCE.md](ACCEPTANCE.md) · **Start:** [START_HERE.md](START_HERE.md) · **Log:** [RUN_LOG.md](RUN_LOG.md)  
**Prior art:** `results/phase5/SURPRISE.md` (simulated only)  
**Notebook:** `docs/runbooks/atlasP5live.ipynb`

## Goal

Re-run the Phase 5 **high_reuse** surprise cell against **real OpenAI-compatible vLLM workers** behind the Atlas gateway, and publish an honest GPU write-up.

## Minimum matrix (required)

| Pattern | Strategies |
| --- | --- |
| `high_reuse` | `round_robin`, `prefix_aware` |

**Strongly recommended also:** `least_load` on high_reuse; `low_reuse` × prefix_aware (sanity: sticky should not dominate).

## Replica strategy (free path)

| Mode | When to use | Label in write-up |
| --- | --- | --- |
| Dual process, split `gpu_memory_utilization` (e.g. 0.4/0.4) | Fits in T4 VRAM | `replica_mode=time_sliced_dual` |
| Sequential isolated runs | Dual OOM | `replica_mode=sequential_isolated` — **weaker**; say so |

See `docs/knowledge/hardware-constraints/FREE_PATH_REPLICAS.md`.

## Artifacts

| Path | Contents |
| --- | --- |
| `results/phase5-live/routing_matrix_live.csv` | Cells with hardware, vllm_version, replica_mode, strategy, pattern, hit%, TTFT p50/p95, skew, n |
| `results/phase5-live/SURPRISE_GPU.md` | Verdict vs Phase 5 sim; hypothesis; caveats |
| `results/phase5-live/README.md` | How to reproduce |
| Optional notebook | `notebooks/colab/phase7_routing_live.ipynb` |

## Run sketch

```powershell
# On Colab/WSL with two vLLM OpenAI servers at :8001 and :8002
# Point configs/models/workers.yaml base_urls at them
$env:ATLAS_STRATEGY = "prefix_aware"
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080

# Drive high_reuse trace via harness extended for live mode OR scripted curl/httpx
# Prefer extending benchmarks/run_routing_matrix.py with --worker-mode live
```

Exact harness flag is an implementation detail — AC requires reproducibility, not a specific CLI name.

## Honesty

- Streaming TTFT from worker client is allowed if labeled; do not mix with Phase 3 batch wall.
- Router hit ≠ engine APC hit.
- Cross-check: same model id as workers YAML; pin vLLM **0.26.0** unless write-up justifies otherwise.

## Out of scope

- TTFT load gate (Phase 8)
- Demo video (Phase 9)
- DistServe / multi-node / RDMA
