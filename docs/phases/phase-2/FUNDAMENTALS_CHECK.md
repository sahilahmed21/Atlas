# Phase 2 — Fundamentals check

For each mechanism: exact failure mode (from Phase 1), mechanism, what it does **not** fix.

| Mechanism | Failure fixed | Does not fix |
| --- | --- | --- |
| Paged allocator | Tests F1: fixed-size KV blocks, allocated on demand and reached through a logical-to-physical block table, bound tail waste under variable sequence lengths. The Phase 1 `+73.7 MB` peak-memory gap is motivation, not proof that paging caused it. | Model weights, activations, non-KV framework allocations, or a real GPU kernel. The simulation must not claim it reproduces the Phase 1 aggregate VRAM gap. |
| Continuous batching | Tests F2: admit requests at decode-step boundaries and execute work for active requests together, instead of treating each threaded `generate()` as an isolated run. Measure busy fraction and completion latency on one deterministic arrival trace. | Capacity limits, true vLLM throughput, fairness/preemption policy, or the exact cause of Phase 1's 5.5× latency cliff; that run has no profiler trace. |
| Prefix cache | Tests F3: reuse KV only when token prefixes match exactly. Phase 1's harness preserves a 23-token configured prefix before appending a request id, so N=8 is a reproducible shared-prefix workload. | Decode cost, cache misses for unique prompts, cache eviction policy, or cross-replica reuse. A hit is not proof of an end-to-end latency win for long generations. |

## Research basis

- [PagedAttention (Kwon et al., SOSP 2023)](https://arxiv.org/abs/2309.06180): fixed-size KV
  blocks and a block table enable non-contiguous, on-demand allocation.
- [vLLM Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/):
  cached prefixes skip prefill only; it does not reduce decode work and offers no benefit without
  matching prefixes.

## Evidence boundary

Phase 2 sims are implemented under `fundamentals/{allocators,schedulers,prefix_cache}/`.
Results live in `results/phase2/`. Mechanism boundaries above still apply: do not claim
these sims reproduce Phase 1 GPU peak VRAM or tokens/s.
