# Atlas — one-sentence framing

> **Production-grade multi-tenant LLM serving behavior on constrained hardware** — a free-tier T4 and a laptop 3050 — without the multi-node / RDMA infrastructure big platforms assume.

## Why this sentence is load-bearing

Every later decision must survive this filter:

| Temptation | Filter answer |
| --- | --- |
| "We need A100 / multi-node for credibility" | No — the constraint *is* the story |
| "Fake disaggregation with two processes and call it DistServe" | No — state as informed future work in Phase 6 |
| "Skip Phase 1 math and jump to vLLM" | No — without the failure curve, before/after is theater |
| "Prefix-aware always wins" | No — Phase 5 must find where it loses |

## What we are *not* building (yet)

- Multi-region failover
- Real RDMA / disaggregated prefill-decode across nodes
- Production billing / Stripe
- Full Kubernetes multi-cluster control plane

Those appear in Phase 6 as **informed future work**, tied back to why this hardware cannot honestly claim them.
