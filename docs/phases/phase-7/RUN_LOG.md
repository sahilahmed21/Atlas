# Phase 7 — Colab run log (2026-08-12)

**Notebook:** `docs/runbooks/atlasP5live.ipynb`  
**Verdict this session:** dual vLLM **infra PASS**; live matrix **NOT run** (wrong git tip).

## Root cause of “simulated” CSV

Colab clone was at GitHub `origin/master` ≈ `0c871bf` (**before** live harness).

| Commit | What |
| --- | --- |
| `0c871bf` | What Colab had — `run_routing_matrix.py` has **no** argparse / live mode |
| `d8ed511` | RED live harness test |
| `517a309` | GREEN `--worker-mode live` |
| `b4305ee` | docs / START_HERE CLI |

Old `main()` ignores CLI flags → full 12-row **sim** matrix → `results/phase5/routing_matrix.csv` with `worker_mode=simulated`.  
Those numbers are **Phase 5 sim only** — **not** Phase 7 GPU evidence.

**Fix before next Colab matrix cell:** push local master (or upload tree ≥ `517a309`), then:

```bash
cd ~/Atlas
git fetch origin && git checkout master && git pull   # or: git checkout 517a309
uv run python benchmarks/run_routing_matrix.py --help | grep worker-mode
# must print --worker-mode; if not, STOP — still on old tip
```

---

## Environment (real)

| Check | Result |
| --- | --- |
| GPU | Tesla T4 |
| CUDA | True |
| torch | 2.11.0+cu128 |
| vLLM | **0.26.0** (pin OK) |
| Model | `Qwen/Qwen2.5-0.5B-Instruct` |
| max_model_len | 2048 |
| FP note | T4 CC 7.5 → bf16 fallback to **fp16** (expected, not a failure) |

## Dual workers (real)

Both on `CUDA_VISIBLE_DEVICES=0`, `gpu_memory_utilization=0.4`, `max_model_len=2048`:

| Port | `/v1/models` | Chat “Say ping” |
| --- | --- | --- |
| 8001 | PASS | PASS (`system_fingerprint` vllm-0.26.0-…) |
| 8002 | PASS | PASS |

→ `replica_mode=time_sliced_dual` **infrastructure** proven on one T4.

## Matrix run attempted (invalid for Phase 7)

Command used flags for live mode, but binary was pre-harness → wrote:

`results/phase5/routing_matrix.csv` (12 rows, **all** `worker_mode=simulated`).

`results/phase5-live/` had **only** README (no live CSV).

Sim headline (cite only as Phase 5): high_reuse prefix_aware p50 **297.5** vs RR **147.5**, hit **95.83%**, skew **1.0**. Full table matches prior `results/phase5/` / notebook output — do **not** put in `SURPRISE_GPU.md` as GPU TTFT.

## AC status after first Colab attempt (pre-live tip)

| AC | Status |
| --- | --- |
| AC-001 real vLLM behind URLs | **Infra PASS** (models + inference). Harness↔gateway live matrix still pending on tip ≥ `517a309` |
| AC-002 live CSV high_reuse × RR + prefix_aware | **FAIL** — no `routing_matrix_live.csv` |
| AC-003 SURPRISE_GPU.md | Not started |
| AC-004 metadata on claims | N/A until live CSV |
| AC-005 claim inventory | Infra note only; no GPU TTFT claims |
| AC-006 no APC/DistServe overclaim | Enforced — sim numbers not rebranded as GPU |

## Live matrix closed (same day, tip ≥ `517a309`)

`results/phase5-live/routing_matrix_live.csv`:

| strategy | TTFT p50 | TTFT p95 | hit% | skew | mode |
| --- | ---: | ---: | ---: | ---: | --- |
| round_robin | 28.557 | 36.400 | 0 | 0.5 | live |
| prefix_aware | 33.320 | 44.787 | 95.83 | 1.0 | live |

**Verdict:** **WEAKENED** — affinity/skew match sim; ~2× TTFT cliff does not. See `SURPRISE_GPU.md`.

| AC | Final |
| --- | --- |
| AC-001–006 | **PASS** — Phase 7 **Done**; Phase 8 may start |

## Next

Phase 8 TTFT / load gate (`docs/phases/phase-8/`).
