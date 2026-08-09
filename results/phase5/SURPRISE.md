# Phase 5 surprise — where prefix-aware loses

**worker_mode:** `simulated` (offline ASGI + `SimulatedWorkerClient`)  
**Not GPU truth.** Soft saturation = `served_count` on the chosen worker + in-flight `loads`.  
**Source:** `results/phase5/routing_matrix.csv` (n=24 per cell)

## Headline cell

| Pattern | Metric | round_robin | prefix_aware | Delta |
| --- | --- | --- | --- | --- |
| **high_reuse** | TTFT p50 (ms) | **147.5** | 297.5 | prefix-aware **2.0× worse** |
| high_reuse | TTFT p95 (ms) | **281.25** | 556.25 | prefix-aware **2.0× worse** |
| high_reuse | router cache hit % | 0 (n/a) | **95.83** | affinity “works” |
| high_reuse | worker skew | 0.5 | **1.0** | all traffic on one replica |

**Verdict:** under high prefix reuse, naive prefix-aware **wins cache hits and loses latency**.

## Hypothesis (tested by the matrix)

1. Shared-prefix affinity claims one owner on first miss, then sticks every subsequent hit to that worker.
2. The simulated worker’s soft saturation grows with `served_count` on that replica.
3. Hit savings (`base_hit << base_miss`) are smaller than the accumulated saturation penalty when skew → 1.0.
4. Round-robin spreads `served_count`, so p50/p95 stay lower even with zero router cache hits.

This matches the failure mode production routers guard with a **TTFT load gate** (e.g. llm-d `maxTTFTPenaltyMs`): break stickiness when the warm replica’s predicted TTFT exceeds a cooler replica by too much.

## Secondary observation

Under **sequential** replay, process-local in-flight `loads` return to 0 between requests, so `least_load` repeatedly picks the lexicographically first idle worker (skew 1.0) and matches prefix-aware latency on these traces. Standing/concurrent load would differentiate them; not claimed here.

## What we did *not* conclude

- No Colab/T4 TTFT or vLLM APC hit rates.
- Router `cache_signal` ≠ engine automatic prefix cache.
- No claim that round-robin always wins on GPU.

## Follow-up (out of scope for Phase 5 close)

- Optional Colab dual time-sliced vLLM re-run of the high_reuse surprise cell.
- TTFT load gate on `PrefixAwareRouter` once the loss case is accepted.
