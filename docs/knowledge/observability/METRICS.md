# Observability — metrics Atlas must emit

| Metric | Why |
| --- | --- |
| TTFT | Prefill health |
| Tokens/s | Decode throughput |
| Queue depth | Autoscaling + routing |
| Cache hit ratio | Prefix / KV effectiveness |
| GPU utilization | Saturation |
| P95 latency | User-visible SLO proxy |
| Error / OOM rate | Failure visibility |

Trace path: Gateway → Router → Worker. Dashboard (5.5) consumes these — not invented UI numbers.
