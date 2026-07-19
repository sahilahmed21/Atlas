# Phase 5.5 — Live dashboard

**Eye-stopper (biggest):** real-time requests → replica choice → cache hit/miss → TTFT / throughput while load fires.

## Must show live

- [ ] Ingest / route decision per request
- [ ] Cache hit vs miss
- [ ] TTFT + tokens/s time series
- [ ] Which replica (time-sliced process id is fine)

## Deliverable

- [ ] `dashboard/` app (simplest stack that works — prefer stdlib/SSE or existing React if already natural)
- [ ] 90-second demo video (link in `docs/phases/phase-5.5/DEMO.md`)
- [ ] Do **not** fake metrics — wire to Phase 4 observability

## Context

If Phase 1–5 numbers are fake, this dashboard is a liability in interviews.
