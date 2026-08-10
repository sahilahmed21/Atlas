# Phase 5.5 — Live dashboard

**Eye-stopper (biggest):** real-time requests → replica choice → cache hit/miss → TTFT / throughput while load fires.

## Must show live

- [x] Ingest / route decision per request
- [x] Cache hit vs miss
- [x] TTFT + tokens/s time series
- [x] Which replica (time-sliced process id is fine)

## Deliverable

- [x] `dashboard/` app (stdlib HTML+JS served by gateway)
- [ ] 90-second demo video (link in `docs/phases/phase-5.5/DEMO.md`) — **manual follow-up**
- [x] Do **not** fake metrics — wire to Phase 4 observability (+ event ring)

## Context

If Phase 1–5 numbers are fake, this dashboard is a liability in interviews.
