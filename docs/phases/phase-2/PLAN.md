# Phase 2 — Execution plan

**Goal:** Build three readable CPU simulations that isolate Phase 1 failure modes F1–F3, measure them on deterministic traces, and record results so Phase 3 can reconcile concepts against vLLM honestly.

**Not in scope:** GPU kernels, FastAPI, tenants, routing, vLLM install, reproducing Phase 1’s aggregate +73.7 MB VRAM gap as “proof.”

**Architecture:** [`ARCHITECTURE.md`](ARCHITECTURE.md) · **Decision:** [`ADR 0004`](../../decisions/0004-phase2-cpu-sims.md) · **Checklist:** [`README.md`](README.md)

---

## Phase 2.0 — Preconditions (done)

| Subphase | Work | Exit check |
| --- | --- | --- |
| 2.0.1 | Phase 1 AC-001–004 complete | `CHECKLIST.md` all `[x]` |
| 2.0.2 | F1–F3 named with CSV evidence | `04_failure_modes.md` |
| 2.0.3 | Mechanism boundaries written | `FUNDAMENTALS_CHECK.md` |
| 2.0.4 | Spec stubs for each toy | `01_` / `02_` / `03_` notes |

---

## Phase 2.1 — Allocator (F1)

**Why:** Separate contiguous over-reservation / fragmentation from theoretical KV bytes under variable sequence length.

| Subphase | Work | Deliverable | Verify |
| --- | --- | --- | --- |
| 2.1.1 | Contiguous-reservation sim | `fundamentals/allocators/` | Reserves `max_len`; tracks unused tail |
| 2.1.2 | Paged block-table sim | same package | On-demand blocks; ≤1 partial block waste/seq |
| 2.1.3 | Fixed variable-`S` trace | shared by both designs | Same requests, same `bytes_per_token=12288`, documented `block_size` |
| 2.1.4 | Emit metrics CSV | `results/phase2/allocator.csv` | reserved/used/free/waste/outcome columns |
| 2.1.5 | One runnable check | `test_*.py` or `__main__` asserts | Paged waste < contiguous waste on that trace |
| 2.1.6 | Write measured results | `01_allocator.md` § Measured | Numbers + “sim vs Phase 1 measured” disclaimer |

**Acceptance:** Contiguous vs paged compared on one trace; docs state which numbers are simulated.

---

## Phase 2.2 — Scheduler (F2)

**Why:** Show static batching idle gaps vs continuous admission under the same arrival/length trace — without claiming it explains Phase 1’s GPU cliff cause.

| Subphase | Work | Deliverable | Verify |
| --- | --- | --- | --- |
| 2.2.1 | Static batching sim | `fundamentals/schedulers/` | Batch-full or timeout → run to completion |
| 2.2.2 | Continuous batching sim | same package | Step: retire → admit → service one unit each |
| 2.2.3 | Deterministic arrival trace + seed | documented in result | Identical input to both |
| 2.2.4 | Metrics | `results/phase2/scheduler.csv` (or summary JSON) | Busy fraction, completion latency, work/time |
| 2.2.5 | One runnable check | test / `__main__` | Continuous busy fraction ≥ static on chosen trace |
| 2.2.6 | Write measured results | `02_scheduler.md` § Measured | Seed, capacity, timeout, budget recorded |

**Acceptance:** Metrics comparable *within* the sim model only — do not map to Phase 1 tok/s.

---

## Phase 2.3 — Prefix cache (F3)

**Why:** Count redundant prefills of a shared token prefix vs a no-reuse workload.

| Subphase | Work | Deliverable | Verify |
| --- | --- | --- | --- |
| 2.3.1 | Token-id prefix hash cache | `fundamentals/prefix_cache/` | Hash token ids, not raw text |
| 2.3.2 | Shared-prefix traffic | Phase 1–shaped 23-token prefix + unique suffixes | Expect 1 prefix prefill + subsequent hits |
| 2.3.3 | Unique-prefix traffic | eight distinct prefixes | Expect 0 hits / 0 avoided prefill |
| 2.3.4 | Metrics | `results/phase2/prefix_cache.csv` | hits, misses, full vs avoided prefill tokens |
| 2.3.5 | One runnable check | test / `__main__` | Shared hits; unique zero hits |
| 2.3.6 | Write measured results | `03_prefix_cache.md` § Measured | Document block-alignment simplification |

**Acceptance:** Prefill accounting only; no decode-speedup claim.

---

## Phase 2.4 — Close-out

| Subphase | Work | Verify |
| --- | --- | --- |
| 2.4.1 | Tick `README.md` checkboxes 2.1–2.3 | All sim items `[x]` |
| 2.4.2 | Confirm `FUNDAMENTALS_CHECK.md` still matches measured language | No overclaim of Phase 1 VRAM |
| 2.4.3 | Optional: short `results/phase2/README.md` listing artifacts | Paths match docs |
| 2.4.4 | Unblock Phase 3 conceptually | Toys exist to diff against vLLM |

**Done when:** Someone else can re-run the three sims from repo + docs alone and get the same tables.

---

## Dependency graph

```text
2.0 (done)
  └─► 2.1 Allocator ──► 2.4 Close-out
  └─► 2.2 Scheduler ──► 2.4
  └─► 2.3 Prefix cache ► 2.4
```

2.1 / 2.2 / 2.3 are independent; preferred order is allocator → scheduler → cache (matches F1→F3 and docs numbering).

---

## Explicit non-goals (this phase)

- F4 preemption / unfair long requests (optional later)
- Cache eviction policy (unless implemented and documented)
- Platform gateway, router, dashboard
- Installing or pinning vLLM (Phase 3)
