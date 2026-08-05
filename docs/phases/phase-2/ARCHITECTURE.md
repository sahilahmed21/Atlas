# Phase 2 — Architecture

**Status:** Done (sims implemented)  
**Audience:** Implementers of Phase 2 toys; Phase 3 readers comparing concepts to vLLM  
**Related:** [`PLAN.md`](PLAN.md) · [`FUNDAMENTALS_CHECK.md`](FUNDAMENTALS_CHECK.md) · [ADR 0004](../../decisions/0004-phase2-cpu-sims.md)

---

## Why this phase exists

Phase 1 measured a **real** failure curve on a laptop RTX 3050 (latency cliff at N=8). It did **not** isolate which serving mechanism failed:

| Phase 1 observation | What it cannot prove alone |
| --- | --- |
| Peak VRAM +73.7 MB vs ~+4.5 MiB KV math | Contiguous KV allocation vs activations vs fragmentation |
| Latency 5.5× at N=8, flat aggregate tok/s | GIL vs kernel serialization vs lack of continuous batching |
| Eight shared-prefix prefills | End-to-end cache speedup (no prefill timer) |

Phase 2 builds **teaching simulations** so each failure mode (F1–F3) has a controlled, reproducible experiment. Phase 3 then diffs these concepts against pinned vLLM source and a real before/after chart — without inventing mechanisms after the fact.

---

## Goals

| ID | Goal | Success look |
| --- | --- | --- |
| G1 | Isolate F1 (allocation waste under variable S) | Contiguous vs paged waste on one deterministic trace |
| G2 | Isolate F2 (static vs continuous packing) | Busy fraction + completion latency on one arrival trace |
| G3 | Isolate F3 (shared prefix recomputation) | Hit/miss + avoided prefill tokens on shared vs unique traffic |
| G4 | Keep toys honest | Docs never claim sims reproduce Phase 1 GPU VRAM or tok/s |
| G5 | Enable Phase 3 | Each toy has a clear concept to map to block manager / scheduler / APC |

### Non-goals

- Production attention kernels or CUDA
- OpenAI gateway, tenants, routing (Phase 4+)
- Matching Phase 1’s 27.7 tok/s or +73.7 MB numerically
- Multi-replica or distributed prefix state

---

## System context

```text
┌─────────────────────────────────────────────────────────────┐
│ Phase 1 (measured, done)                                    │
│  naive_hf_load.py → results/phase1/*.csv → F1, F2, F3       │
└───────────────────────────┬─────────────────────────────────┘
                            │ inputs (evidence + acceptance hooks)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 2 (this architecture) — CPU only, fundamentals/       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ allocators/  │  │ schedulers/  │  │ prefix_cache/    │  │
│  │ contiguous   │  │ static       │  │ token-id hash    │  │
│  │ vs paged     │  │ vs continuous│  │ longest prefix   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                   │             │
│         └────────────┬────┴───────────────────┘             │
│                      ▼                                      │
│              results/phase2/*.csv                           │
│              docs/phases/phase-2/0{1,2,3}_*.md (measured)   │
└───────────────────────────┬─────────────────────────────────┘
                            │ conceptual artifacts
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 3 (later) — Colab/Kaggle T4 + pinned vLLM             │
│  Source + chart reconciliation against these toys           │
└─────────────────────────────────────────────────────────────┘
```

Phase 2 does **not** sit on the request path of `platform/` or `workers/`. Per [ADR 0002](../../decisions/0002-repo-layout.md), toys stay under `fundamentals/`.

---

## Component design

### 1. Allocator (`fundamentals/allocators/`)

| Concern | Contiguous design | Paged design |
| --- | --- | --- |
| Reservation | One span sized to declared `max_len` | Fixed-size blocks on demand |
| Mapping | N/A (single buffer) | Logical block index → physical block id |
| Waste metric | `reserved − used` (+ external fragmentation if free spans don’t fit) | At most one partial block per active sequence |
| Byte scale | `bytes_per_token` (default 12288 from Phase 1 Qwen math) | Same |

**Achieves:** G1 — shows when over-reservation / fragmentation hurts *within the model*, not on GPU peak allocation.

### 2. Scheduler (`fundamentals/schedulers/`)

| Concern | Static | Continuous |
| --- | --- | --- |
| Admission | Wait for batch full or timeout | Admit at step boundaries up to capacity |
| Work unit | Run admitted batch to completion | One decode/service unit per active request per step |
| Metrics | Busy fraction, queue wait, completion latency, work/time | Same |

**Achieves:** G2 — utilization and latency under identical arrivals; units are simulated ticks, not GPU tokens/s.

### 3. Prefix cache (`fundamentals/prefix_cache/`)

| Concern | Behavior |
| --- | --- |
| Key | Hash of exact token-id prefix (block-aligned if documented) |
| Hit | Charge only suffix as prefill work |
| Miss | Charge full prompt; insert eligible prefixes |
| Traffic A | Shared Phase 1–shaped prefix + unique suffixes |
| Traffic B | Unique prefixes (expect zero benefit) |

**Achieves:** G3 — prefill accounting only; matches APC’s “prefill only” boundary.

---

## Data & artifacts

| Artifact | Role |
| --- | --- |
| `results/phase2/allocator.csv` | Per-request reserved/used/waste/outcome for both designs |
| `results/phase2/scheduler.csv` (or summary) | Busy fraction, latencies, seed, capacity |
| `results/phase2/prefix_cache.csv` | Hits, misses, avoided prefill tokens |
| `01_allocator.md` / `02_scheduler.md` / `03_prefix_cache.md` | Narrative + measured tables |
| One small test or `__main__` assert per toy | Prevents silent logic breakage |

Traces must be **deterministic** (fixed lists and/or seeded generators recorded in the result section).

---

## Constraints & honesty rules

1. **CPU sims only** — no torch required for Phase 2 toys.
2. **Same trace, both designs** — never compare contiguous run A to paged run B with different inputs.
3. **Label simulated vs measured** — Phase 1 CSV is measured; Phase 2 CSV is simulated.
4. **No cross-phase metric laundry** — do not claim continuous batching “fixed” the 5.5× cliff until Phase 3 measures vLLM on hardware.
5. **Readable over clever** — prefer ~50–150 lines per toy over a shared framework.

---

## What we achieve when Phase 2 is done

1. **Interview-defensible mechanism literacy** — you can walk F1→paging, F2→continuous batch, F3→prefix cache with *your* tables.
2. **Phase 3 readiness** — concrete toys to diff against vLLM block manager, scheduler, and automatic prefix caching.
3. **Scope discipline** — platform work stays blocked until these fundamentals exist (no router theater).

---

## Exit criteria (phase-level)

- [x] Three packages under `fundamentals/{allocators,schedulers,prefix_cache}/` runnable via `uv run`
- [x] Three result artifacts under `results/phase2/`
- [x] Measured sections filled in `01_` / `02_` / `03_`
- [x] `PLAN.md` / `README.md` checkboxes for 2.1–2.3 marked done
- [x] Claims in docs match [G4](#goals) (no Phase 1 VRAM/tok/s overclaim)
