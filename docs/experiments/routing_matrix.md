# Routing experiment matrix (Phase 5)

**Status:** Offline complete (`worker_mode=simulated`)  
**Data:** [`results/phase5/routing_matrix.csv`](../../results/phase5/routing_matrix.csv)  
**Surprise:** [`results/phase5/SURPRISE.md`](../../results/phase5/SURPRISE.md)  
**Reproduce:** `uv run python benchmarks/run_routing_matrix.py`

Cells: TTFT p50 / p95 (ms), tokens/s mean, router cache hit %, worker skew (max share).

| Traffic \ Strategy | Round robin | Least load | Prefix-aware |
| --- | --- | --- | --- |
| High prefix reuse | p50 **147.5** / p95 **281.3**; t/s 8.69; hit n/a; skew 0.50 | p50 297.5 / p95 556.3; t/s 5.49; hit n/a; skew 1.00 | p50 297.5 / p95 556.3; t/s 5.49; **hit 95.8%**; skew **1.00** — **loses vs RR on latency** |
| Low prefix reuse | p50 **237.5** / p95 **371.3**; t/s 4.81; skew 0.50 | p50 387.5 / p95 646.3; t/s 3.35; skew 1.00 | p50 387.5 / p95 646.3; hit 0%; skew 1.00 — no affinity win |
| Bursty | p50 **167.5** / p95 **281.3**; t/s 8.22; skew 0.50 | p50 297.5 / p95 556.3; skew 1.00 | p50 297.5 / p95 556.3; hit 91.7%; skew 1.00 — loses vs RR |
| Steady | p50 **147.5** / p95 **281.3**; t/s 8.69; skew 0.50 | p50 297.5 / p95 556.3; skew 1.00 | p50 297.5 / p95 556.3; hit 91.7%; skew 1.00 — loses vs RR |

**Required surprise cell:** high_reuse × prefix_aware — high router hit rate, worse TTFT than round_robin because sticky skew saturates one simulated replica.

Honesty: simulated latency model only; not Colab/vLLM APC.
