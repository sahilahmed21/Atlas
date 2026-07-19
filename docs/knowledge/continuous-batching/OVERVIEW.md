# Continuous batching

**Static batching:** Wait until batch full or timeout → GPU idle gaps.  
**Continuous batching:** When one sequence finishes, insert a new one into the running batch; decode steps stay packed.

**Phase 1 link:** Concurrent naive `generate()` is *not* continuous batching — each call is its own graph / its own world. That is why Phase 1 fails differently from vLLM.

**Phase 2:** Simulate idle fraction under Poisson arrivals for static vs continuous.
