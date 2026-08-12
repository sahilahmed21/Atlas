# Resume bullets

Defensible only. Source: `docs/phases/phase-6/CLAIM_INVENTORY.md`.

- Built and measured a concurrent HuggingFace baseline for **Qwen2.5-0.5B** on a **4 GiB RTX 3050**; documented a **5.5×** median latency cliff at N=8 (**9242 ms** p50) with CSV + chart (`results/phase1/`).
- Reconciled that naive path against pinned **vLLM 0.26.0** on a free-tier **T4**, keeping the overlay explicitly **cross-hardware** (`results/phase3/`).
- Implemented an OpenAI-compatible FastAPI gateway with YAML multi-tenant auth, process-local RPM, and prefix-aware / round-robin / least-load routing (`platform/`).
- Ran an offline routing matrix and found the loss case: **high_reuse** prefix-aware hit% **95.8** with **2× worse** simulated TTFT p50 vs round-robin due to replica saturation (`results/phase5/SURPRISE.md`) — not cited as GPU TTFT.
- Shipped a live request-path dashboard (`/dashboard/`) fed by the same `observe_request` path as Prometheus; demo video deferred.

**Do not put on a resume:** DistServe, RDMA, multi-node llm-d deploy, KEDA-in-production, or “prefix-aware improved latency by X%.”
