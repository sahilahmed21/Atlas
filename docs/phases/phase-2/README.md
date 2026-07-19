# Phase 2 — Toy mechanisms

**Status:** Blocked until Phase 1 AC pass  
**Hardware:** Laptop  
**Eye-stopper:** None new — instruments that make Phase 3 reconciliation honest

## Subsystems (standalone sims)

| Toy | Path | Fixes failure |
| --- | --- | --- |
| Naive vs paged allocator | `fundamentals/allocators/` | F1 |
| Static vs continuous scheduler | `fundamentals/schedulers/` | F2 |
| Prefix-hash cache | `fundamentals/prefix_cache/` | F3 |

## Steps

### 2.1 Allocator
- [ ] Simulate block table vs contiguous tensor
- [ ] Metric: wasted bytes vs fragmentation under variable S
- [ ] Doc: `docs/phases/phase-2/01_allocator.md`

### 2.2 Scheduler
- [ ] Simulate request arrival; compare GPU busy %
- [ ] Doc: `docs/phases/phase-2/02_scheduler.md`

### 2.3 Prefix cache
- [ ] Hash prefix tokens; count hit/miss under shared-prompt traffic
- [ ] Doc: `docs/phases/phase-2/03_prefix_cache.md`

### 2.4 Fundamentals check
- [ ] For each toy, one paragraph: failure mode from Phase 1 math, not a blog paraphrase
- [ ] `docs/phases/phase-2/FUNDAMENTALS_CHECK.md`

## Context

Toys are **readable simulations**, not production kernels. Phase 3 diffs them against vLLM source conceptually.
