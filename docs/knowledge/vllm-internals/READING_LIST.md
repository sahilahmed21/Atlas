# vLLM internals — reading list

| Area | Upstream path (approx) | Atlas note |
| --- | --- | --- |
| Block manager | Current docs: [PagedAttention design](https://docs.vllm.ai/en/latest/design/paged_attention/); exact implementation path must come from the pinned checkout. | Compare Phase 2's block table and tail-waste model with real cache-block allocation, sharing, and preemption. |
| Scheduler | Current docs: [vLLM overview](https://docs.vllm.ai/) describes continuous batching; exact implementation path must come from the pinned checkout. | Compare the toy's fixed service steps with real token budgets, admission, and scheduling policy. |
| Prefix caching | Current docs: [Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/). | Verify exact token/block hashing, cacheability, eviction, and the prefill-only performance boundary. |
| OpenAI API server | Current docs: [OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/). | Phase 4 should use the pinned server contract, not this planning note, for the worker client. |

**Pinned vLLM version:** Not pinned. `pyproject.toml` declares unversioned `vllm` only in the
Phase 3+ GPU group, and the repository has no vLLM source checkout.

Log version, commit/tag, and file:line references when doing the Phase 3 source diff. Current
documentation is design context only and is not evidence of an installed implementation.
