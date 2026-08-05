# Phase 1 — Failure modes → Phase 2 inputs

Each mode must cite Phase 1 evidence (math row or CSV row).

| ID | Failure mode | Evidence | Phase 2 toy that addresses it |
| --- | --- | --- | --- |
| F1 | Unexplained peak-memory overhead should be separated from theoretical KV use | `naive_load.csv` N=1→N=8: peak VRAM grew **969.2 → 1042.9 MB (+73.7 MB)** while the KV math for 7 extra requests at `S≈55` predicts only **+4.5 MiB** — **~16× total peak-memory overhead**. This aggregate metric cannot prove contiguous KV allocation or identify its cause. | Naive vs paged allocator |
| F2 | Per-request concurrent generation does not scale throughput proportionally | `naive_load.csv`: 8× offered load returned **1.45× aggregate throughput** (19.2 → 27.7 tok/s, already peaked at N=4) while p50 latency rose **5.5×** (1671 → 9242 ms). The harness has no trace to prove why. | Static vs continuous scheduler |
| F3 | Shared prompt prefixes are recomputed by this harness | `naive_hf_load.py` appends only ` [req=i]` after the configured prompt, preserving its 23-token prefix (`configs/models/phase1.yaml`; every CSV row reports `prompt_tokens=23`). The harness has no prefix cache, so N=8 performs eight prefills of that shared prefix. | Prefix-hash cache |
| F4 | _(optional)_ No preemption / unfair long requests | Not measured — the sweep used one uniform `max_new_tokens=32` per run, so head-of-line blocking never had a chance to appear | Note only; deferred to Phase 2 scheduler work |

## Fundamentals check (must answer in one sentence each)

1. **F1 is addressed by paging because:** fixed-size KV blocks are allocated on demand and mapped by
   a block table, bounding tail waste to a partially filled block; the Phase 2 simulation must show
   whether that improves the Phase 1 proxy, rather than claiming it explains the 16× aggregate gap.
2. **F2 is addressed by continuous batching because:** a scheduler can admit arrivals and run decode
   steps for in-flight requests together, unlike this harness's independent `generate()` calls; the
   Phase 2 simulation must measure utilization and throughput before claiming the cause of the cliff.
3. **F3 is addressed by prefix caching because:** cached KV for an exact token prefix can be reused,
   so this workload's shared configured prefix needs one initial prefill and can produce seven
   subsequent hits; it does not remove decode work or help unique prefixes.

## Phase 2 acceptance hook

Each toy must be measured against these same numbers, not against a textbook claim:

- Paged allocator: report allocated-vs-theoretical KV ratio under variable sequence lengths; compare it
  to a contiguous-reservation simulation, not the aggregate 16× GPU-peak ratio.
- Continuous batching: report busy fraction and completion latency under the same deterministic arrival
  trace; do not compare simulated tok/s directly to the GPU's 27.7 tok/s.
- Prefix cache: report prefill count at N=8 with a shared token prefix; target 1 rather than 8, plus
  a no-reuse case showing no claimed benefit.
