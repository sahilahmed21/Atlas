# Prefix caching

**Idea:** Identical token prefixes → reuse computed KV (hash of token ids).

**High reuse traffic:** shared system prompts, RAG template + same doc prefix.  
**Low reuse:** unique user text → cache adds lookup cost / memory pressure for little hit rate.

**Phase 5 mandate:** Find a pattern where prefix-aware **routing** loses (e.g. low reuse + sticky imbalance, or thrashing between replicas).

## Hierarchy (research → platform)

Local engine cache (vLLM) vs router-level affinity (Atlas). Document both; do not conflate.
