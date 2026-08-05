# Phase 3 — Toy vs vLLM source diff

| Concept | Your toy | vLLM (file/version) | Match? |
| --- | --- | --- | --- |
| Block allocation | Pending Phase 2 toy: on-demand fixed-size blocks plus logical-to-physical block table. | Not yet pinned or inspected. Current design reference: [PagedAttention docs](https://docs.vllm.ai/en/latest/design/paged_attention/). Record the installed version and exact source path during Phase 3. | Pending source read |
| Scheduling | Pending Phase 2 sim: deterministic step admission and one service unit per active request. | Not yet pinned or inspected. Compare real token-budget/admission/preemption behavior rather than assuming a one-step toy is equivalent. | Pending source read |
| Prefix / automatic prefix caching | Pending Phase 2 toy: longest exact token-id prefix; cacheable work is prefill only. | Not yet pinned or inspected. Current behavior reference: [Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/). Record cache-block and hash semantics from the pinned source. | Pending source read |

## What I misunderstood before reading source

**Pending Phase 3 source reconciliation.** No vLLM version is pinned in `pyproject.toml` and no
vLLM source checkout or runtime artifact exists in this repository. Do not turn the current design
references into a source-level claim until the Phase 3 environment is installed and inspected.
