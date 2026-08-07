# Atlas session handoff

**Date:** 2026-08-07 (this session) · prior arc late July–early August 2026  
**Branch:** `master` (local **ahead of origin by 11 commits** — not pushed)  
**HEAD:** `9fcd902` — `fix: Phase 3 batch generate, NVML VRAM, hardware honesty (GREEN)`  
**Next step:** **Phase 4** — platform gateway + router (blocked until now; Phase 3 eye-stopper exists)  
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
| 3 vLLM reconciliation | **Done** | `results/phase3/naive_vs_vllm.png` + CSV (Colab T4) |
| 4 Platform + router | **Do next** | `platform/` is README-only |
| 5 Routing experiment | Blocked | Find where prefix-aware **loses** |
| 5.5 Live dashboard | Blocked | Real metrics only |
| 6 Write-up + pitch | Blocked | Honest constraint → future work |

Phase index: `docs/phases/README.md`. Root checklist still shows Phase 3 unchecked until AC-005.

---

## 3. What this session accomplished (2026-08-07)

### Context load
- Read prior handoff; confirmed Phase 0–2 done; started Phase 3 with TDD + intent-driven ACs + ponytail + karpathy.
- Exa MCP not available → verified vLLM pin via web search (stable **0.26.0**, 2026-07-27).

### Phase 3 offline slice (AC-001–004)
1. **ACCEPTANCE:** `docs/phases/phase-3/ACCEPTANCE.md`
2. **Pin:** `0.26.0` in `vllm_load.PINNED_VLLM_VERSION` + `configs/models/phase3.yaml` + READING_LIST
3. **Harness:** `fundamentals/experiments/vllm_load.py`
4. **Overlay:** `fundamentals/experiments/plot_naive_vs_vllm.py`
5. **Source diff:** `docs/phases/phase-3/02_source_diff.md` (3 sim / 3 diff / 1 misunderstanding vs tag `v0.26.0`)
6. **Notebook:** `notebooks/colab/phase3_vllm.ipynb`
7. **TDD evidence:** `docs/testing/phase-3.tdd.md`

### Code review → Critical/High fixes (fundamental, not band-aids)

Review found threaded N×`generate([one])` would **not** measure continuous batching. Fixes landed:

| Bug | Fix now in tree |
| --- | --- |
| Threaded singles | **One** `llm.generate([p0..pN-1])` (vLLM offline CB API) |
| Identical prompts | `make_prompts` → Phase 1 shape `[req=i]` |
| Torch allocator VRAM | **NVML** `pynvml` used-bytes (`vram_source=nvml`) |
| Unlabeled 3050 vs T4 | `overlay_title` + hardware fields + `cross-hardware` warning |
| Bare `models/` gitignore hid `configs/models/` | Changed to **`/models/`** (repo-root only) |
| Docs said `uv sync --group gpu` | `gpu = []` on purpose; install via `+cu129` wheel |

**Also:** warmup before timed sweep; `statistics.median` for tok/s; empty-file CSV header parity; `verify_wsl_vllm.py` asserts pin.

### Git commits this session (Phase 3)

```
9fcd902 fix: Phase 3 batch generate, NVML VRAM, hardware honesty (GREEN)
2907147 test: reproduce Phase 3 CB/VRAM/hardware honesty bugs (RED)
e902035 chore: track phase3.yaml and results/phase3 placeholder
e59de3e feat: Phase 3 overlay plotter, vLLM harness, pin 0.26.0 (GREEN)
540670b test: add Phase 3 overlay and vLLM load reproducers (RED)
```

Prior Phase 2 sequence still on branch (`cec3081` … `1afef1e`).

**Do not force-push.** Push only if the user asks (`git push -u origin HEAD`).

### Tests at handoff
```text
uv run pytest fundamentals/experiments fundamentals/allocators fundamentals/schedulers fundamentals/prefix_cache -q
→ 25 passed
```

### Working tree notes
- Uncommitted: `docs/README.md`, `uv.lock` (may be dirty from resolve attempts) — review before commit.
- This handoff file should be committed if the user wants it tracked.

---

## 4. Key measured findings (cite these; don’t invent)

### Phase 1 (GPU, laptop RTX 3050, Qwen2.5-0.5B-Instruct @ `7ae5576`)

| N | p50 latency (ms) | vs N=1 | peak VRAM (MB) |
| --- | --- | --- | --- |
| 1 | 1671 | 1.0× | 969.2 |
| 2 | 2614 | 1.6× | 988.3 |
| 4 | 4405 | 2.6× | 1001.8 |
| 8 | 9242 | **5.5× cliff** | 1042.9 |

- **No CUDA OOM**; failure = latency cliff (`cliff_factor=5.0`).
- Only `max_new_tokens=32` ran (128 never ran). Seq-length OOM sweep deferred.
- Data: `results/phase1/naive_load.csv`

### Phase 1 → Phase 2 failure modes

| ID | Mode | Phase 2 toy |
| --- | --- | --- |
| F1 | Peak-memory overhead vs theoretical KV | Allocator |
| F2 | Concurrent `generate()` doesn’t scale throughput | Scheduler |
| F3 | Shared prompt prefix recomputed | Prefix cache |
| F4 | Preemption / HOL — **not measured** | — |

### Phase 2 (CPU sims — not GPU truth)

| Toy | Headline | Artifact |
| --- | --- | --- |
| Allocator | Contiguous waste **49,004,544** B vs paged **442,368** B | `results/phase2/allocator.csv` |
| Scheduler | Busy frac static **0.3846** vs continuous **0.5417** | `results/phase2/scheduler.csv` |
| Prefix cache | Shared **7 hits / 1 miss**; unique **0 hits** | `results/phase2/prefix_cache.csv` |

### Phase 3 (not measured yet)

**Do not invent** `vllm_load.csv` or overlay PNG numbers. Offline tooling only until Colab/Kaggle run.

---

## 5. Honesty rules (do not regress)

1. Phase 2 sims **≠** Phase 1 GPU metrics. Label **simulated vs measured**.
2. No GIL/kernel root-cause without a profiler trace.
3. Prefix cache: **prefill accounting only**; toy keys whole 23-token prefix ≠ vLLM block-aligned APC.
4. Phase 3 latency is **batch wall** (`ttft_proxy=batch_wall`), not streaming TTFT.
5. Phase 3 VRAM is **NVML used**; Phase 1 is torch peak — different meters; say so in captions.
6. Overlay of laptop-3050 vs colab-t4 is **cross-hardware** — chart title must say so (already implemented).
7. Never fake Phase 3–5.5 results or dashboard metrics.
8. `platform/`, `workers/`, `dashboard/` are stubs.

---

## 6. Code map — where things live

### Phase 1 (real GPU)

| Path | Role |
| --- | --- |
| `configs/models/phase1.yaml` | Model, revision `7ae5576…`, sweeps, cliff |
| `fundamentals/experiments/naive_hf_load.py` | Threaded HF `generate()` + `[req=i]` → CSV |
| `fundamentals/experiments/plot_failure_curve.py` | Cliff/OOM plot |
| `fundamentals/experiments/test_plot_failure_curve.py` | Classification tests |
| `results/phase1/naive_load.csv` | Measured |
| `results/phase1/oom_latency_curve.png` | Eye-stopper |

### Phase 2 (CPU toys)

| Path | Role |
| --- | --- |
| `fundamentals/allocators/allocator_sim.py` | Contiguous vs paged |
| `fundamentals/schedulers/scheduler_sim.py` | Static vs continuous |
| `fundamentals/prefix_cache/prefix_cache_sim.py` | Prefix hash cache |
| `results/phase2/*.csv` | Sim outputs |
| `docs/phases/phase-2/` | PLAN, ARCHITECTURE, ACCEPTANCE, 01–03 |
| `docs/testing/phase-2.tdd.md` | RED/GREEN evidence |
| `docs/decisions/0004-phase2-cpu-sims.md` | ADR |

### Phase 3 (harness ready; GPU pending)

| Path | Role |
| --- | --- |
| `configs/models/phase3.yaml` | Same model revision; `hardware_label: colab-t4`; `vllm_version: "0.26.0"` |
| `fundamentals/experiments/vllm_load.py` | Batched `LLM.generate`, NVML, pin assert, CSV |
| `fundamentals/experiments/plot_naive_vs_vllm.py` | Overlay + hardware honesty |
| `fundamentals/experiments/test_vllm_load.py` | CSV/pin/CB/NVML tests |
| `fundamentals/experiments/test_plot_naive_vs_vllm.py` | Join/title/gitignore tests |
| `notebooks/colab/phase3_vllm.ipynb` | Thin Colab entry |
| `scripts/verify_wsl_vllm.py` | Assert pin `0.26.0` |
| `docs/phases/phase-3/` | README, ACCEPTANCE, 01_before_after, 02_source_diff |
| `docs/knowledge/vllm-internals/READING_LIST.md` | Pin + `+cu129` install |
| `docs/runbooks/COLAB_KAGGLE.md` | How to install/run on T4 |
| `docs/testing/phase-3.tdd.md` | TDD evidence incl. review fixes |
| `results/phase3/` | **Placeholder only** (`.gitkeep`) — no measured CSV/PNG |

### Stubs (not implemented)

`platform/`, `workers/`, `dashboard/`, `benchmarks/`, `deploy/`

### Dependency landmine

- `pyproject.toml` `[dependency-groups] gpu = []` **on purpose**.
- Declaring `vllm==0.26.0` breaks laptop `uv` resolve (wants `torch==2.11.0` vs cu124 index).
- Colab T4 (CUDA 12.x drivers): install  
  `vllm-0.26.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl`  
  from the [v0.26.0 release](https://github.com/vllm-project/vllm/releases/tag/v0.26.0).  
  Default PyPI wheel wants CUDA 13 (`libcudart.so.13`).

### Gitignore

- Use **`/models/`** (repo-root weights only). Bare `models/` incorrectly ignored `configs/models/`.
- `phase3.yaml` is tracked (`git add -f` was needed historically; rule now fixed).

---

## 7. How Phase 3 harness works (current correct design)

1. Load `phase3.yaml`; assert config pin == `PINNED_VLLM_VERSION` (`0.26.0`).
2. Import vLLM; `assert_runtime_vllm_matches_pin(vllm.__version__)`.
3. Build `LLM(model=…, revision=…, dtype=float16, trust_remote_code=False)`.
4. **Warmup** one small batch (discarded).
5. For each `n` in `[1,2,4,8]`:
   - `prompts = [f"{template} [req={i}]" for i in range(n)]`
   - **One** `llm.generate(prompts, SamplingParams(max_tokens=32, temperature=0.0))`
   - `total_ms` = batch wall; notes include `ttft_proxy=batch_wall; vram_source=nvml; batch_generate=1`
   - Cliff stop vs N=1 baseline × `cliff_factor` (same philosophy as Phase 1)
6. Overlay joins Phase 1 + Phase 3 CSVs on concurrency; title labels both hardwares.

**Wrong (fixed):** `ThreadPoolExecutor` × N `generate([one_prompt])` — does not measure CB.

---

## 8. Reproduce commands

```powershell
cd C:\projects\Atlas
uv sync

# All fundamentals tests (25 expected)
uv run pytest fundamentals/experiments fundamentals/allocators fundamentals/schedulers fundamentals/prefix_cache -q

# Phase 2 CSV regen
uv run python fundamentals/allocators/allocator_sim.py
uv run python fundamentals/schedulers/scheduler_sim.py
uv run python fundamentals/prefix_cache/prefix_cache_sim.py

# Phase 1 chart
uv run python fundamentals/experiments/plot_failure_curve.py

# Phase 3 overlay (fails until vllm_load.csv exists — correct)
# uv run python fundamentals/experiments/plot_naive_vs_vllm.py
```

### Colab / Kaggle T4 (AC-005)

Follow `docs/runbooks/COLAB_KAGGLE.md` or notebook:

```bash
pip install https://github.com/vllm-project/vllm/releases/download/v0.26.0/vllm-0.26.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
python scripts/verify_wsl_vllm.py
python fundamentals/experiments/vllm_load.py
python fundamentals/experiments/plot_naive_vs_vllm.py
# Download results/phase3/ then fill docs/phases/phase-3/01_before_after.md
```

Weights: repo-root `models/` gitignored. Phase 1 used curl into `models/Qwen2.5-0.5B-Instruct` (HF Hub hung). See `docs/phases/phase-1/RUN_LOG.md`.

---

## 9. What to do next (strict order)

**Only AC-005 remains for Phase 3:**

1. Open Colab/Kaggle **T4** runtime.
2. Install `+cu129` wheel; verify `vllm.__version__ == "0.26.0"`.
3. Ensure Phase 1 CSV is present (clone repo or upload `results/phase1/naive_load.csv`).
4. Run `vllm_load.py` → `results/phase3/vllm_load.csv` (**measured only**).
5. Run `plot_naive_vs_vllm.py` → `naive_vs_vllm.png`.
6. Caption `01_before_after.md` (version, wheel, hardware, TTFT proxy, VRAM meter, cliff points).
7. Tick Phase 3 checkboxes / root README Phase 3 when real artifacts exist.

**Do not** start Phase 4 until the before/after artifact exists.

### Medium review items still open (optional polish)

- Colab notebook could add explicit clone/`%cd` bootstrap.
- Source diff could add exact file:line from `v0.26.0` tree (substance already present).

---

## 10. Preferred working style

Skills that worked this session: **ponytail**, **karpathy-guidelines**, **tdd-workflow**, **intent-driven-development**.

- Prefer `uv run` / `uv sync`; Python `>=3.11,<3.14`.
- RED commit → GREEN commit when TDD active; otherwise commit only if user asks.
- PowerShell: `git commit -m "message"` (no bash heredocs).
- Fewest files; unique test module basenames.
- Verify claims (web/docs) — no assumptions on vLLM install/CUDA.

---

## 11. Known gaps / landmines

| Gap | Detail |
| --- | --- |
| Phase 3 GPU | No `vllm_load.csv` / PNG yet |
| Phase 1 partial | `max_new_tokens=128` never ran; no high-S KV OOM |
| Empty `gpu` group | Never tell people `uv sync --group gpu` installs vLLM |
| Cross-hardware chart | Expected for 3050 vs T4; must stay labeled |
| Pitch | `docs/pitch/ONE_PARAGRAPH.md` mixes measured + future — don’t claim unbuilt pieces |
| Dirty files | `docs/README.md`, `uv.lock` may be uncommitted |
| Ahead of origin | 11 commits local; push only on request |

---

## 12. Prompt starter for the next chat

```text
Continue Atlas from @docs/HANDOFF.md.

Phase 0–2 done. Phase 3 offline harness/plot/source-diff/pin 0.26.0 done
(after code-review fixes: batch generate, [req=i], NVML, hardware labels).
AC-005 remains: run on Colab/Kaggle T4 with +cu129 wheel, write
results/phase3/vllm_load.csv + naive_vs_vllm.png, caption 01_before_after.md.

Do not invent GPU results. Do not start Phase 4 until the overlay exists.
Respect honesty rules (sim ≠ measured; batch_wall ≠ streaming TTFT;
NVML ≠ torch peak; cross-hardware must stay labeled).

Follow docs/phases/phase-3/README.md and docs/runbooks/COLAB_KAGGLE.md.
```

---

## 13. Quick links

| Need | Path |
| --- | --- |
| Phase index | `docs/phases/README.md` |
| Phase 3 ACs | `docs/phases/phase-3/ACCEPTANCE.md` |
| Phase 3 TDD | `docs/testing/phase-3.tdd.md` |
| Colab runbook | `docs/runbooks/COLAB_KAGGLE.md` |
| vLLM pin / wheel | `docs/knowledge/vllm-internals/READING_LIST.md` |
| Phase 2 architecture | `docs/phases/phase-2/ARCHITECTURE.md` |
| Phase 1 curve | `docs/phases/phase-1/03_failure_curve.md` |
| MVP architecture | `docs/architecture/MVP_ARCHITECTURE.md` |
| ADR index | `docs/decisions/README.md` |
