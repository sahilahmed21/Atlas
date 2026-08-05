# ADR 0004 — Phase 2 as CPU teaching simulations

**Status:** Accepted  
**Date:** 2026-08-06  
**Deciders:** Atlas maintainers (this session)

## Context

Phase 1 produced a measured latency cliff and named failure modes F1–F3, but those modes are not isolated in the GPU harness. Phase 2 must teach allocation, continuous batching, and prefix caching without a free-tier multi-GPU stack and without inventing production kernels. We need a clear place for toys that Phase 3 can later reconcile against vLLM.

## Decision

Implement Phase 2 as three independent **CPU simulations** under `fundamentals/allocators/`, `fundamentals/schedulers/`, and `fundamentals/prefix_cache/`. Each toy runs deterministic traces, writes metrics under `results/phase2/`, and documents measured results in `docs/phases/phase-2/`. Simulations are conceptual models for Phase 3 source diffs — not drop-in replacements for vLLM or the Phase 4 platform path.

## Alternatives considered

### Alternative 1: Patch HuggingFace / run real paging on GPU in Phase 2
- **Pros:** Closer to production numbers earlier
- **Cons:** Unreadable; couples learning to CUDA quirks; hard to isolate one mechanism
- **Why not:** Phase 2 eye-stopper is conceptual honesty for Phase 3, not a second failure curve

### Alternative 2: Shared “mini serving framework” with plugins for all three
- **Pros:** One codebase, shared traces
- **Cons:** Over-engineering for three small sims; obscures the mechanism under framework glue
- **Why not:** Violates ADR 0002 spirit (keep toys simple) and YAGNI for Phase 2 size

### Alternative 3: Docs-only Phase 2 (no code)
- **Pros:** Fast
- **Cons:** No reproducible artifact; Phase 3 “diff against toys” becomes vapor
- **Why not:** Phase index requires measured sim results, not paraphrases of blogs

## Consequences

### Positive
- Each failure mode has a controlled, reproducible experiment
- Laptop-only; no Colab required for Phase 2
- Clear handoff into Phase 3 (concepts + CSVs to reconcile)

### Negative
- Simulated metrics are not GPU truth; easy to overclaim if docs are sloppy
- Extra discipline required to avoid comparing sim tok/s to Phase 1 CSV

### Risks
- **Risk:** Readers treat paged-sim waste as explaining Phase 1’s +73.7 MB VRAM  
  **Mitigation:** `FUNDAMENTALS_CHECK.md` + architecture honesty rules; measured sections must label sim vs measured

## Links

- Plan: [`docs/phases/phase-2/PLAN.md`](../phases/phase-2/PLAN.md)
- Architecture: [`docs/phases/phase-2/ARCHITECTURE.md`](../phases/phase-2/ARCHITECTURE.md)
- Layout: [ADR 0002](0002-repo-layout.md)
