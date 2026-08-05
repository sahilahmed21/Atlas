# Phase 2 — Prefix cache notes

## What F3 looked like in Phase 1

`naive_hf_load.py` forms each request as the configured prompt followed by ` [req=i]`. The fixed
configured portion tokenizes to 23 tokens in every committed CSV row, so the N=8 workload has a
shared prefix before request-specific text. The naive harness has no cache and therefore prefilled
that prefix eight times. No timing isolates prefill, so Phase 1 does not measure a cache speedup.

## Cache design

Hash the exact token-id prefix, not raw prompt text. Store the cached prefix length and an abstract
KV-block reference. For each request:

1. tokenize the prompt;
2. search for the longest cached token-id prefix;
3. on a hit, reuse its prefix representation and count only the suffix as prefill work;
4. on a miss, prefill the full prompt and insert eligible block-aligned prefixes.

The block-alignment condition matters: vLLM's automatic prefix caching reuses cached KV blocks, not
arbitrary text substrings. This toy may model one block size explicitly, but it must document that
simplification.

## Required traffic

| Trace | Expected cache behavior |
| --- | --- |
| Eight prompts with the Phase 1 shared prefix and unique suffixes | One initial prefix prefill, then seven hits if the shared prefix is cacheable. |
| Eight unique token prefixes | Zero hits; demonstrate that no prefill work is claimed as saved. |
| Repeated prefix after eviction/clear | Document whether the toy treats it as a miss; eviction is optional unless implemented. |

## Limits

Prefix caching reduces prefill computation only. It does not remove decode work, guarantee a
latency improvement for long outputs, coordinate cache state between replicas, or solve routing.
These limits match [vLLM's Automatic Prefix Caching documentation](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/).

## Measured sim result

**Simulated.** Token ids only (not raw prompt text). Cache keys the full shared prefix
length **23** (teaching simplification — not vLLM block-aligned APC pages).

| Traffic | Hits | Misses | Prefill tokens charged | Avoided prefill tokens |
| --- | --- | --- | --- | --- |
| Shared prefix (8 prompts) | **7** | **1** | 31 | **161** (= 7 × 23) |
| Unique prefixes (8 prompts) | **0** | **8** | 192 | **0** |

Artifact: `results/phase2/prefix_cache.csv`  
Reproduce: `uv run python fundamentals/prefix_cache/prefix_cache_sim.py`  
Tests: `uv run pytest fundamentals/prefix_cache`

Prefill accounting only — no decode-latency claim. Eviction not implemented (clear = cold cache).
