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
| Phase 7 infra: Colab T4 dual vLLM 0.26.0 on :8001/:8002 (`gpu_memory_utilization=0.4`), Qwen2.5-0.5B — `/v1/models` + chat inference PASS | `docs/phases/phase-7/RUN_LOG.md`, notebook `docs/runbooks/atlasP5live.ipynb` | **Infra only** — no live routing TTFT CSV yet |

## Forbidden

| Temptation | Why |
| --- | --- |
| “We run DistServe / RDMA / multi-node” | Not built; free path cannot honestly claim it |
| Phase 5 numbers as Colab/GPU TTFT | Simulated soft saturation only |
| 2026-08-12 Colab matrix CSV as Phase 7 live evidence | Ran pre-`517a309` tip; wrote `worker_mode=simulated` to `results/phase5/` |
| Generic “prefix-aware improved X%” | Our headline cell is a *loss* case |
| Empty demo video URL | Honesty: omit until a real recording exists |
| Mixing Phase 1 torch peak with Phase 3 NVML as one meter | Different meters |
| Unlabeled 3050↔T4 overlay as same-GPU win | Must stay labeled cross-hardware |
| Multi-replica-safe RPM / queue / events | Process-local |
| KEDA as a live cluster | `deploy/keda/` is a planning sketch |

## Future work (say so; do not present as done)

| Topic | Wording | Link |
| --- | --- | --- |
| Prefill/decode disaggregation | Needs multiple GPUs + fast interconnect; interference exists on one T4 but cannot be scheduled away by topology | `docs/research/distserve/ATLAS_RELEVANCE.md` |
| Production llm-d / multi-node | Inspired by llm-d cache-aware concerns; not an llm-d deploy | `docs/research/llm-d/ATLAS_RELEVANCE.md` |
| Live GPU routing matrix + SURPRISE_GPU | Dual workers up; need tip ≥ `517a309` then high_reuse live CSV | **Phase 7** `docs/phases/phase-7/RUN_LOG.md` |
| TTFT load gate on prefix-aware | Break stickiness when warm replica too hot | **Phase 8** `docs/phases/phase-8/` |
| Phase 5.5 90s video + public package | UI + runbook ready; video + README sell in Phase 9 | **Phase 9** `docs/phases/phase-9/` · `docs/phases/phase-5.5/DEMO.md` |
| Optional JD widener | One of RAG / eval / cost — only after Phase 9 | **Phase 10** `docs/phases/phase-10/` |
| Live gateway↔vLLM Colab matrix (full) | Covered by Phase 7 minimum cell; full 3×4 optional | HANDOFF / Phase 7 README |

Hire-signal order: [NEXT_ARC.md](NEXT_ARC.md).
