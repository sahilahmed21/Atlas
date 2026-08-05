# Phase 6 — Honest write-up + pitch

**Status:** Not started — only Phase 1 has measured artifacts. Phase 6 must not claim implementation
or results for the remaining phases before those artifacts exist.

## README narrative arc

1. **Constraint:** name the laptop/free-tier T4 boundary and explicitly exclude multi-node/RDMA claims.
2. **Naive approach:** cite Phase 1's own model, hardware, CSV, and measured N=8 latency cliff.
3. **What was built:** enumerate only directories and features that exist at publication time; distinguish
   Phase 2 simulations from the Phase 4 serving path.
4. **Surprising result:** cite the exact Phase 5 matrix cell in which prefix-aware routing loses.
5. **Live demo:** link the Phase 5.5 recording and identify the real metric source.
6. **Future work:** explain that prefill/decode disaggregation needs multiple GPUs and fast
   interconnect; link the DistServe/llm-d research notes rather than promising it as implemented.

## Pitch paragraph

Draft in `docs/pitch/ONE_PARAGRAPH.md`. Rehearse until every clause is defensible.

## Resume bullets (draft)

- **Not claimable yet:** Phase 2–5.5 artifacts do not exist, so do not write performance or platform
  bullets for them.
- **Phase 1 candidate, after final review:** Built and measured a concurrent HuggingFace baseline for
  Qwen2.5-0.5B on a 4 GiB RTX 3050; documented a 5.5× latency cliff at N=8 with the CSV and chart.
- **Future candidate:** After Phase 5, state the routing metric, hardware, workload, baseline, and
  the observed case where prefix-aware routing underperformed. Do not use a generic "improved X%"
  statement without the corresponding result artifact.
