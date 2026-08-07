# Phase 3 — Toy vs vLLM source diff

**Pinned version:** vLLM **0.26.0** (tag `v0.26.0`, released 2026-07-27).  
Evidence: [release](https://github.com/vllm-project/vllm/releases/tag/v0.26.0), design doc at tag, reading list.

| Concept | Your toy (Phase 2) | vLLM `v0.26.0` | Match? |
| --- | --- | --- | --- |
| Block allocation | Fixed-size blocks; paged reserves `ceil(used/block)*block`; per-request waste accounting (`fundamentals/allocators/allocator_sim.py`, `block_size=16`) | `vllm/v1/core/kv_cache_manager.py` + block pool / free queue; physical blocks with refcounts; allocation via `allocate_slots` / `get_computed_blocks` (see `docs/design/prefix_caching.md` @ tag) | **Partial** — same idea (fixed-size KV blocks + indirection), but vLLM is a shared pool with refcount + eviction, not per-request waste sums |
| Scheduling | Discrete ticks; continuous admits up to capacity and advances every active request by 1 service unit (`scheduler_sim.py`) | `vllm/v1/core/sched/scheduler.py` — `schedule()` returns `{req_id: num_tokens}` per engine step (chunked prefill, decode=1, prefix hits, speculative budgets) | **Partial** — both are continuous-batching flavored; vLLM schedules **token budgets**, not toy “+1 per tick” |
| Prefix / APC | SHA-256 of whole cacheable prefix (23 tokens); hit → charge suffix only; prefill accounting only (`prefix_cache_sim.py`) | Hash chain over **full blocks only**: `hash(parent_hash, block_tokens, extras)`; default `sha256` since v0.11; LRU free-queue eviction (`docs/design/prefix_caching.md` @ `v0.26.0`) | **No** at key granularity — toy is whole-prefix; vLLM is block-aligned APC |

## 3 similarities

1. **Paged KV blocks** — both treat KV memory as fixed-size blocks rather than one contiguous per-request reservation.
2. **Continuous batching spirit** — both keep a running set of requests and admit work each step instead of only static full batches.
3. **Prefix reuse is prefill-side** — both avoid recomputing shared prompt work; neither toy nor this phase claims a decode-speedup story from prefix hits alone.

## 3 differences

1. **Hash granularity** — toy hashes the entire 23-token prefix once; vLLM hashes **full blocks** with a parent-hash chain (partial blocks are not cacheable).
2. **Shared pool + eviction** — vLLM uses a global block pool, refcounts, and LRU eviction from the free queue; the toy never evicts and never shares physical pages across a heap model.
3. **Scheduler unit** — toy advances one abstract service unit per active request per tick; vLLM’s scheduler allocates a **variable token count** per request per forward pass (chunked prefill, speculative decode, etc.).

## What I misunderstood before reading source

**The Phase 2 prefix cache is not a miniature Automatic Prefix Caching.** Treating a hit on the whole 23-token prefix as “like vLLM APC” overstates the mechanism: vLLM only caches **full blocks**, keys include the **parent block hash** (and extras such as LoRA / multimodal / cache salt), and reuse is mediated by the KV cache manager + scheduler admission — not a single dict of prefix digests. Document that boundary in any Phase 3–5 routing claims.

## Runtime measurement status

Measured on Colab T4 via `notebooks/colab/phase3actual.ipynb` (vLLM **0.26.0+cu129**):

| N | batch wall (ms) | NVML used (MB) |
| --- | --- | --- |
| 1 | 266 | 14956 |
| 2 | 210 | 14956 |
| 4 | 216 | 14956 |
| 8 | 229 | 14956 |

Artifacts: `results/phase3/vllm_load.csv`, `naive_vs_vllm.png`. Caption: `01_before_after.md`.
