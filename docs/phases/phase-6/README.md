# Phase 6 — Honest write-up + pitch

**Status:** Done (2026-08-10)  
**ACs:** [ACCEPTANCE.md](ACCEPTANCE.md) · **Claims:** [CLAIM_INVENTORY.md](CLAIM_INVENTORY.md)  
**Pitch:** [docs/pitch/ONE_PARAGRAPH.md](../../pitch/ONE_PARAGRAPH.md) · **Resume:** [docs/pitch/RESUME_BULLETS.md](../../pitch/RESUME_BULLETS.md)

## Narrative arc

1. **Constraint.** Laptop RTX 3050 4 GiB + free-tier Colab/Kaggle T4. Multi-replica = time-sliced or sequential. Multi-node / RDMA / DistServe are **not** claimed ([framing](../../framing/ONE_SENTENCE.md)).

2. **Naive approach.** Qwen2.5-0.5B HuggingFace on the 3050: N=8 median latency **9242 ms**, **5.5×** N=1, peak VRAM ~1.04 GiB (`results/phase1/naive_load.csv`, `oom_latency_curve.png`).

3. **What was built.** Phase 2 CPU toys (`results/phase2/`) inform understanding; they are **not** GPU metrics. Phase 4+ ships a real FastAPI OpenAI-compatible path: YAML tenants, process-local RPM, prefix-aware / RR / least-load routers, Prometheus + request-path events (`platform/`).

4. **Reconcile.** Pinned vLLM **0.26.0+cu129** on T4; overlay vs Phase 1 is **cross-hardware** (`results/phase3/`).

5. **Surprising result.** Offline sim matrix, **high_reuse × prefix_aware**: router hit% **95.83** but TTFT p50 **2× worse** than round-robin (sticky saturation). Not GPU truth (`results/phase5/SURPRISE.md`).

6. **Live demo.** `/dashboard/` + `/atlas/events` from the same `observe_request` path as Prometheus. Video deferred; runbook in [phase-5.5/DEMO.md](../phase-5.5/DEMO.md).

7. **Future work.** Prefill/decode disaggregation needs multiple GPUs and fast interconnect — state as informed research, not implemented ([DistServe](../../research/distserve/ATLAS_RELEVANCE.md), [llm-d](../../research/llm-d/ATLAS_RELEVANCE.md)). Optional follow-ups: TTFT load gate, Colab dual-vLLM re-run, 90s video.
