# Atlas session handoff

**Date:** 2026-08-06 (work spanned late July–early August 2026 docs/runs)  
**Branch:** `master` (local **ahead of origin by 6 commits** — not pushed)  
**Next phase:** **Phase 3** — real vLLM + source reconciliation on Colab/Kaggle T4  
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
| 2 Toy allocator / scheduler / prefix cache | **Done** | `results/phase2/*.csv` + sims under `fundamentals/` |
| 3 vLLM reconciliation | **Do next** | Need `results/phase3/naive_vs_vllm.png` |
| 4 Platform + router | Blocked on 3 | `platform/` is README-only |
| 5 Routing experiment | Blocked | Find where prefix-aware **loses** |
| 5.5 Live dashboard | Blocked | Real metrics only |
| 6 Write-up + pitch | Blocked | Honest constraint → future work |

Root checklist marks Phase 0–2 `[x]`. Phase index: `docs/phases/README.md`.

---

## 3. What this session (and recent work) accomplished

### Docs / planning (earlier in arc)
- Filled Phase 1 docs from measured evidence; corrected overclaims (don’t attribute cliff to GIL without a trace; don’t treat +73.7 MB VRAM as proof of contiguous KV).
- Filled Phase 2 specs: `PLAN.md`, `ARCHITECTURE.md`, `ACCEPTANCE.md`, `FUNDAMENTALS_CHECK.md`, `01_`/`02_`/`03_` templates → measured sections.
- **ADR 0004:** Phase 2 = CPU teaching simulations (`docs/decisions/0004-phase2-cpu-sims.md`).
- Expanded Phase 4–6 docs as **requirements/pending**, not fake results.

### Phase 2 implementation (TDD)
Executed Phase 2 with RED→GREEN checkpoints:

1. Allocator (F1) — contiguous vs paged  
2. Scheduler (F2) — static vs continuous  
3. Prefix cache (F3) — shared vs unique token prefixes  

Evidence report: `docs/testing/phase-2.tdd.md`  
Acceptance: `docs/phases/phase-2/ACCEPTANCE.md`  
**11 tests pass:** Phase 1 plot tests + 3 Phase 2 suites.

### Git commits on `master` (Phase 2 TDD sequence)

```
cec3081 feat: Phase 2 prefix-cache sim and close-out (GREEN)
f772005 test: add Phase 2 prefix-cache sim reproducers (RED)
8f87c85 feat: Phase 2 static vs continuous scheduler sim (GREEN)
13c2bd5 test: add Phase 2 scheduler sim reproducers (RED)
0ff015c feat: Phase 2 contiguous vs paged allocator sim (GREEN)
1afef1e test: add Phase 2 allocator sim reproducers (RED)
9267213 Complete Phase 1 naive-load experiments and land Phase 2 CPU-sim plan.
```

**Do not force-push.** Push only if the user asks (`git push -u origin HEAD`).

---

## 4. Key measured findings (cite these; don’t invent)

### Phase 1 (GPU, laptop RTX 3050, Qwen2.5-0.5B-Instruct @ `7ae5576`)

| N | p50 latency (ms) | vs N=1 | peak VRAM (MB) |
| --- | --- | --- | --- |
| 1 | 1671 | 1.0× | 969.2 |
| 2 | 2614 | 1.6× | 988.3 |
| 4 | 4405 | 2.6× | 1001.8 |
| 8 | 9242 | **5.5× cliff** | 1042.9 |

- **No CUDA OOM** in this sweep; failure = latency cliff (`cliff_factor=5.0`).
- Aggregate tok/s ~19.2 → ~27.7 (peaked by N=4) — concurrency didn’t buy proportional work.
- Config listed `max_new_tokens` 32 and 128; **only 32 ran** (cliff stop). Documented in `RUN_LOG.md`.
- Sequence-length sweep (`S=2048/4096`) **deferred** — KV OOM prediction untested.
- Weights term ~3% of measured N=1 peak; good. KV term not stressed at `S≈55`.

Data: `results/phase1/naive_load.csv`  
Narrative: `docs/phases/phase-1/03_failure_curve.md`, `04_failure_modes.md`

### Phase 1 → Phase 2 failure modes

| ID | Mode | Phase 2 toy |
| --- | --- | --- |
| F1 | Peak-memory overhead vs theoretical KV (motivation, not proof of contiguous KV) | Allocator |
| F2 | Concurrent `generate()` doesn’t scale throughput proportionally | Scheduler |
| F3 | Shared prompt prefix recomputed (harness has no cache) | Prefix cache |
| F4 | Preemption / HOL — **not measured**, optional later |

### Phase 2 (CPU sims — not GPU truth)

| Toy | Headline result | Artifact |
| --- | --- | --- |
| Allocator | Contiguous waste **49,004,544** B vs paged **442,368** B | `results/phase2/allocator.csv` |
| Scheduler | Busy frac static **0.3846** vs continuous **0.5417** | `results/phase2/scheduler.csv` |
| Prefix cache | Shared: **7 hits / 1 miss**, avoided 161 tokens; unique: **0 hits** | `results/phase2/prefix_cache.csv` |

Constants: `bytes_per_token=12288` (Phase 1 Qwen math), `block_size=16`, scheduler `capacity=4`, static `batch_size=4`/`timeout=5`, prefix length `23`.

---

## 5. Honesty rules (do not regress)

1. Phase 2 sims **do not** explain Phase 1’s +73.7 MB VRAM or 27.7 tok/s. Label **simulated vs measured**.
2. No GIL/kernel root-cause claim without a profiler trace.
3. Prefix cache: **prefill accounting only** — no decode speedup claim.
4. Prefix cache keys whole 23-token prefix (teaching simplification) — **not** vLLM block-aligned APC; say so in Phase 3 diffs.
5. Contiguous allocator model is **per-request max_len reserve**, not a full shared-heap fragmentation sim.
6. Never fake Phase 3–5.5 results or dashboard metrics.
7. `platform/`, `workers/`, `dashboard/` are **stubs** — deps in `pyproject.toml` for Phase 4+ are declared early, not implemented.

---

## 6. Code map — what file does what

### Phase 1 (real GPU)

| Path | Role |
| --- | --- |
| `configs/models/phase1.yaml` | Model, revision, prompt, sweeps, cliff |
| `fundamentals/experiments/naive_hf_load.py` | Concurrent HF `generate()` → CSV |
| `fundamentals/experiments/plot_failure_curve.py` | Load CSV, mark oom/cliff, plot PNG |
| `fundamentals/experiments/test_plot_failure_curve.py` | Classification unit tests |
| `results/phase1/naive_load.csv` | Measured sweep |
| `results/phase1/oom_latency_curve.png` | Eye-stopper chart |

### Phase 2 (CPU toys)

| Path | Role |
| --- | --- |
| `fundamentals/allocators/allocator_sim.py` | Contiguous vs paged |
| `fundamentals/allocators/test_allocator_sim.py` | AC-001 tests |
| `fundamentals/schedulers/scheduler_sim.py` | Static vs continuous |
| `fundamentals/schedulers/test_scheduler_sim.py` | AC-002 tests |
| `fundamentals/prefix_cache/prefix_cache_sim.py` | Token-id prefix hash cache |
| `fundamentals/prefix_cache/test_prefix_cache_sim.py` | AC-003 tests |
| `results/phase2/*.csv` | Sim outputs |

**Naming note:** modules use unique basenames (`*_sim.py` / `test_*_sim.py`) so one `pytest` invocation can collect all three packages without import collisions.

### Phase 2 docs

| Path | Role |
| --- | --- |
| `docs/phases/phase-2/PLAN.md` | Subphases 2.0–2.4 |
| `docs/phases/phase-2/ARCHITECTURE.md` | Goals, components, exit criteria |
| `docs/phases/phase-2/ACCEPTANCE.md` | AC-001–004 |
| `docs/phases/phase-2/01_allocator.md` | Spec + measured |
| `docs/phases/phase-2/02_scheduler.md` | Spec + measured |
| `docs/phases/phase-2/03_prefix_cache.md` | Spec + measured |
| `docs/phases/phase-2/FUNDAMENTALS_CHECK.md` | Mechanism ↔ failure boundaries |
| `docs/decisions/0004-phase2-cpu-sims.md` | ADR: CPU sims |
| `docs/testing/phase-2.tdd.md` | RED/GREEN evidence |

### Empty / stub (do not assume implemented)

- `platform/`, `workers/`, `dashboard/`, `benchmarks/`, `deploy/` — README only  
- No `results/phase3/` or `phase5/` yet  
- vLLM pin **0.26.0** enforced in `vllm_load.PINNED_VLLM_VERSION` + `phase3.yaml`; `pyproject.toml` `[dependency-groups] gpu` is **empty** (cu124 resolve conflict). Install via `+cu129` wheel on T4 — see READING_LIST / COLAB_KAGGLE runbook.  

---

## 7. How each Phase 2 toy works (short)

**Allocator:** Fixed trace of `(request_id, max_len, used)`. Contiguous reserves `max_len * bytes_per_token`. Paged reserves `ceil(used/block_size)*block_size * bytes_per_token`. Compare total waste.

**Scheduler:** Discrete ticks. Static waits until batch full or timeout, then runs that batch to completion (all members advance each tick). Continuous each tick: admit up to capacity, advance every active request by 1. Busy fraction = busy_ticks / (busy+idle).

**Prefix cache:** Prompts as token-id tuples. Hash prefix with SHA-256. On miss, insert cacheable length-23 prefix. On hit, charge only suffix as prefill. Shared traffic = Phase 1–shaped shared prefix + unique suffix; unique traffic = distinct prefixes.

---

## 8. Reproduce commands

```powershell
cd C:\projects\Atlas
uv sync

# Phase 1 tests + Phase 2 tests
uv run pytest fundamentals/experiments fundamentals/allocators fundamentals/schedulers fundamentals/prefix_cache -q

# Regenerate Phase 2 CSVs
uv run python fundamentals/allocators/allocator_sim.py
uv run python fundamentals/schedulers/scheduler_sim.py
uv run python fundamentals/prefix_cache/prefix_cache_sim.py

# Phase 1 chart (needs CSV present)
uv run python fundamentals/experiments/plot_failure_curve.py

# Phase 1 GPU sweep (needs local weights under models/ — gitignored)
# uv run python fundamentals/experiments/naive_hf_load.py
```

Weights: `models/` is gitignored. Phase 1 used `curl` into `models/Qwen2.5-0.5B-Instruct` because HF Hub Python client hung (Xet). See `docs/phases/phase-1/RUN_LOG.md`.

Config is tracked: `configs/models/phase1.yaml` (not ignored by `models/` rule).

---

## 9. What to do next — Phase 3

**Spec:** `docs/phases/phase-3/README.md`  
**Hardware:** Colab / Kaggle T4 (vLLM not native Windows — install pin `0.26.0` via `+cu129` wheel; see `docs/runbooks/COLAB_KAGGLE.md`)  
**Eye-stopper:** Naive (Phase 1) + vLLM on **one** chart → `results/phase3/naive_vs_vllm.png`

### Suggested order

1. Pin a **specific vLLM version** and record it (`docs/knowledge/vllm-internals/READING_LIST.md` is currently “not pinned”).
2. Same model family if VRAM allows (Qwen2.5-0.5B); else document downsize.
3. Same concurrency philosophy as Phase 1 → `results/phase3/vllm_load.csv`.
4. Overlay chart + caption in `docs/phases/phase-3/01_before_after.md`.
5. Source reconciliation vs toys in `02_source_diff.md` (3 similarities, 3 differences, 1 thing toy got wrong).
6. Notebook: `notebooks/colab/phase3_vllm.ipynb` when executing.

Smoke helper (minimal): `scripts/verify_wsl_vllm.py`.

**Do not** start Phase 4 platform until Phase 3 has a real before/after artifact (project rule: no eye-stopper theater).

---

## 10. Preferred working style for the next chat

Skills often used: **ponytail** (minimal code), **karpathy-guidelines** (think / simple / surgical / verify), **tdd-workflow** (RED before GREEN, evidence in `docs/testing/`), **intent-driven-development** (ACs before build), **architecture-decision-records** (repo uses `docs/decisions/`, not `docs/adr/`).

- Prefer `uv run` / `uv sync`; Python 3.11.
- Fewest files; unique test module basenames if multiple packages.
- Checkpoint commits OK when TDD skill is active; otherwise only commit if user asks.
- PowerShell: no bash heredocs — use `git commit -m "message"`.

---

## 11. Known gaps / landmines

| Gap | Detail |
| --- | --- |
| Partial Phase 1 sweep | `max_new_tokens=128` never ran |
| No seq-length OOM | KV math at high S untested |
| Leftover file risk | If `fundamentals/schedulers/sim.py` reappears, it’s a rename leftover — canonical is `scheduler_sim.py` |
| Observability sketch | `docker-compose.obs.yml` / `configs/observability/` may exist untracked from earlier work — Phase 4 territory |
| Pitch | `docs/pitch/ONE_PARAGRAPH.md` mixes measured Phase 1 with future tense — don’t claim unbuilt pieces |
| Working tree | At handoff write time: clean for Phase 2; `master` ahead 6 of `origin` |

---

## 12. Prompt starter for the next chat

```text
Continue Atlas from @docs/HANDOFF.md.
Phase 0–2 are done. Start Phase 3 (vLLM on Colab/Kaggle T4): pin vLLM,
same load shape as Phase 1, results/phase3/, before/after chart, source
diff vs Phase 2 toys. Follow docs/phases/phase-3/README.md. Do not invent
results. Respect honesty rules in the handoff (sim ≠ Phase 1 GPU metrics).
```

---

## 13. Quick links

| Need | Path |
| --- | --- |
| Phase index | `docs/phases/README.md` |
| Phase 2 architecture | `docs/phases/phase-2/ARCHITECTURE.md` |
| Phase 3 start | `docs/phases/phase-3/README.md` |
| Phase 1 curve story | `docs/phases/phase-1/03_failure_curve.md` |
| MVP architecture | `docs/architecture/MVP_ARCHITECTURE.md` |
| ADR index | `docs/decisions/README.md` |
