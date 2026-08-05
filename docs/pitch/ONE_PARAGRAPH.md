# One-paragraph pitch (draft)

**Status:** Phase 6 draft. Only the Phase 1 failure curve is currently an artifact; the remaining
claims below are the intended narrative and must be revised as phases ship.

Atlas is a research-oriented LLM serving project for demonstrating production multi-tenant serving
*behavior* on constrained free-tier GPUs rather than assuming multi-node RDMA infrastructure. Its
first measured artifact is a Qwen2.5-0.5B HuggingFace baseline on a 4 GiB RTX 3050: at N=8,
median latency reached 9242 ms, 5.5× the N=1 baseline, while peak VRAM remained about 1.04 GiB.
Next, Atlas will build readable allocation, batching, and prefix-cache simulations; reconcile them
against a pinned vLLM run; and test cache-aware routing against simple baselines, including a case
where it loses. The eventual public artifact set is the Phase 1 failure curve, a vLLM comparison,
the routing matrix, and a dashboard backed by the same request path—not a claim that unbuilt
components already run in production.

Rehearse only the measured Phase 1 paragraph today. Promote later clauses from future tense only
when their named file, run, and chart exist.
