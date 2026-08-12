# Phase 7 surprise — live GPU vs Phase 5 sim

**Date:** 2026-08-12  
**worker_mode:** `live`  
**hardware:** Colab Tesla T4  
**vLLM:** 0.26.0  
**model:** `Qwen/Qwen2.5-0.5B-Instruct`  
**replica_mode:** `time_sliced_dual` (`gpu_memory_utilization≈0.4` each on :8001 / :8002)  
**Source:** `results/phase5-live/routing_matrix_live.csv` (n=24 per cell)  
**Metric:** streaming TTFT from Atlas → OpenAI-compatible workers (not Phase 3 batch wall)

## Headline cell (live)

| Pattern | Metric | round_robin | prefix_aware | Delta |
| --- | --- | --- | --- | --- |
| **high_reuse** | TTFT p50 (ms) | **28.557** | 33.320 | prefix-aware **~1.17×** (~17% slower) |
| high_reuse | TTFT p95 (ms) | **36.400** | 44.787 | prefix-aware **~1.23×** (~23% slower) |
| high_reuse | router cache hit % | 0 | **95.83** | affinity “works” |
| high_reuse | worker skew | 0.5 | **1.0** | all traffic on one replica |

**Verdict: WEAKENED** (not confirmed, not refuted).

Routing / affinity behavior matches the sim (hit% 95.83, skew 1.0). The **large** sim TTFT penalty (~2×) does **not** appear on live dual vLLM; a **small** sticky penalty remains (~1.17–1.23×).

## Compare to Phase 5 sim

| | Sim RR | Sim prefix | Live RR | Live prefix |
| --- | ---: | ---: | ---: | ---: |
| TTFT p50 (ms) | 147.5 | 297.5 | 28.557 | 33.320 |
| TTFT p95 (ms) | 281.25 | 556.25 | 36.400 | 44.787 |
| Cache hit % | 0 | 95.83 | 0 | 95.83 |
| Skew | 0.5 | 1.0 | 0.5 | 1.0 |

Sim p50 ratio ≈ **2.02×**; live p50 ratio ≈ **1.17×**. Absolute ms are not comparable across soft-sat sim vs real T4 streaming.

## Hypothesis

1. Router sticky affinity still concentrates load (skew 1.0) and still yields high `cache_signal` hits.
2. The simulated worker’s soft saturation overstated how badly one warm replica hurts TTFT on this tiny model + time-sliced T4.
3. Real engines absorb sequential sticky traffic better than the toy latency model — direction of the effect survives; magnitude does not.
4. Phase 8 load gate remains motivated (small live penalty + production-shaped failure mode) but is no longer justified by a dramatic GPU 2× cliff.

## What we did *not* conclude

- Router `cache_signal` ≠ vLLM Automatic Prefix Caching hit rate.
- No DistServe / multi-node / RDMA claim.
- No claim that round-robin always wins on every GPU/model.
- Do not mix these streaming TTFT numbers with Phase 3 batch-wall latency.

## Follow-up

- **Phase 8:** TTFT / load gate on `PrefixAwareRouter` (recover sticky hits without paying even the small live penalty under hotter load).
- **Phase 9:** demo + public package citing this WEAKENED verdict honestly.
