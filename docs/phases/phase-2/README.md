# Phase 2 — Toy mechanisms

**Status:** Ready — Phase 1 AC-001–AC-004 are evidenced in the committed docs and artifacts
**Hardware:** Laptop  
**Eye-stopper:** None new — instruments that make Phase 3 reconciliation honest

**Plan:** [`PLAN.md`](PLAN.md) · **Architecture:** [`ARCHITECTURE.md`](ARCHITECTURE.md) · **ADR:** [`0004`](../../decisions/0004-phase2-cpu-sims.md)

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
- [x] For each toy, define the Phase 1 evidence boundary and mechanism; results remain pending
- [x] `docs/phases/phase-2/FUNDAMENTALS_CHECK.md`

## Context

Toys are **readable simulations**, not production kernels. Phase 3 diffs them against vLLM source conceptually.
