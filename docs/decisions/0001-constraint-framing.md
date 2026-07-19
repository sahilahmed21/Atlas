# ADR 0001 — Constraint framing drives scope

**Status:** Accepted  
**Date:** 2026-07-19

## Decision

Atlas optimizes for *production-grade serving behavior on constrained hardware* (free T4 + laptop 3050). Multi-node / RDMA features are deferred, not simulated as if real.

## Consequences

- Disaggregation = Phase 6 future work only  
- Eye-stoppers must use measured data on this hardware  
- ₹0 path is a feature of the story
