# ADR 0003 — Free-path multi-replica strategy

**Status:** Accepted  
**Date:** 2026-07-19

## Decision

For routing experiments: use (1) time-sliced dual vLLM on one GPU and/or (2) sequential isolated runs per strategy. Do not require rented multi-GPU.

## Consequences

- Router interfaces talk to worker URLs, not GPU indices  
- Benchmarks prefer sequential for cleanliness; dual process for live dashboard
