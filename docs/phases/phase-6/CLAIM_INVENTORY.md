# Phase 6 — Claim inventory

Gate for pitch / README / resume. Every public number must appear here as **allowed**, or stay out.

## Allowed (cite these)

| Claim | Evidence | Caveat |
| --- | --- | --- |
| Framing: multi-tenant serving *behavior* on free-path GPUs; no multi-node/RDMA assumed | `docs/framing/ONE_SENTENCE.md` | Constraint is the story |
| Phase 1: Qwen2.5-0.5B HF on RTX 3050 4 GiB; N=8 p50 **9242 ms** ≈ **5.5×** N=1 (**1671 ms**); peak VRAM ~**1043 MB** | `results/phase1/naive_load.csv`, `oom_latency_curve.png` | torch peak VRAM, not NVML |
| Phase 2: toy allocator / scheduler / prefix-cache sims exist | `results/phase2/*.csv`, `fundamentals/` | CPU sims ≠ GPU metrics |
| Phase 3: vLLM **0.26.0+cu129** on Colab T4; batch wall ~210–266 ms N=1..8; ~15 GB flat NVML | `results/phase3/vllm_load.csv`, `naive_vs_vllm.png` | Overlay is **cross-hardware** (3050 vs T4); latency = batch wall, not streaming TTFT |
| Phase 4: FastAPI OpenAI-compatible gateway, YAML tenants, process-local RPM, router strategies, Prometheus | `platform/` | Offline-hardened; live dual-vLLM optional |
| Phase 5 high_reuse × prefix_aware: hit% **95.83**, skew **1.0**, TTFT p50 **297.5** vs RR **147.5** (2× worse) | `results/phase5/routing_matrix.csv`, `SURPRISE.md` | **`worker_mode=simulated` only** — not GPU TTFT / vLLM APC |
| Phase 5.5: live `/dashboard/` + `/atlas/events` from same `observe_request` path as Prometheus | `dashboard/`, `platform/observability/`, `docs/phases/phase-5.5/DEMO.md` | Process-local event ring; no prompt text; **video not recorded** |
| Phase 7 live high_reuse on Colab T4 dual vLLM 0.26.0 (`time_sliced_dual`): RR TTFT p50 **28.557** / p95 **36.400**; prefix_aware p50 **33.320** / p95 **44.787**, hit% **95.83**, skew **1.0** (~1.17× p50 vs RR) | `results/phase5-live/routing_matrix_live.csv`, `SURPRISE_GPU.md` | Streaming TTFT; router hit ≠ vLLM APC; **WEAKENS** sim’s ~2× cliff |
| Phase 7 verdict: sim magnitude **weakened**; affinity/skew pattern **preserved** | `SURPRISE_GPU.md` | Do not say “confirmed 2× GPU penalty” |

## Forbidden

| Temptation | Why |
| --- | --- |
| “We run DistServe / RDMA / multi-node” | Not built; free path cannot honestly claim it |
| Phase 5 numbers as Colab/GPU TTFT | Simulated soft saturation only |
| Early 2026-08-12 Colab matrix under `results/phase5/` as Phase 7 live evidence | Pre-`517a309` tip; `worker_mode=simulated` |
| Live router hit% as “vLLM APC hit rate” | Atlas `cache_signal` only |
| “Prefix-aware is 2× worse on GPU” | Live shows ~1.17× p50 — sim magnitude weakened |
| Generic “prefix-aware improved X%” | Headline cells are sticky *loss* (small live, large sim) |
| Empty demo video URL | Honesty: omit until a real recording exists |
| Mixing Phase 1 torch peak with Phase 3 NVML as one meter | Different meters |
| Mixing Phase 3 batch wall with Phase 7 streaming TTFT | Different meters |
| Unlabeled 3050↔T4 overlay as same-GPU win | Must stay labeled cross-hardware |
| Multi-replica-safe RPM / queue / events | Process-local |
| KEDA as a live cluster | `deploy/keda/` is a planning sketch |

## Future work (say so; do not present as done)

| Topic | Wording | Link |
| --- | --- | --- |
| Prefill/decode disaggregation | Needs multiple GPUs + fast interconnect; interference exists on one T4 but cannot be scheduled away by topology | `docs/research/distserve/ATLAS_RELEVANCE.md` |
| Production llm-d / multi-node | Inspired by llm-d cache-aware concerns; not an llm-d deploy | `docs/research/llm-d/ATLAS_RELEVANCE.md` |
| TTFT load gate on prefix-aware | Break stickiness when warm replica too hot — still useful after weakened live gap | **Phase 8** `docs/phases/phase-8/` |
| Phase 5.5 90s video + public package | UI + runbook ready; cite WEAKENED live verdict honestly | **Phase 9** `docs/phases/phase-9/` · `docs/phases/phase-5.5/DEMO.md` |
| Optional JD widener | One of RAG / eval / cost — only after Phase 9 | **Phase 10** `docs/phases/phase-10/` |
| Optional fuller live matrix | least_load / low_reuse cells — not required for Phase 7 close | Phase 7 README |

Hire-signal order: [NEXT_ARC.md](NEXT_ARC.md).
