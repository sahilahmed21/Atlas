# Phase 2 — Scheduler notes

## What F2 looked like in Phase 1

The threaded HuggingFace harness reached 27.7 aggregate generated tokens/s at N=8 versus 19.2 at
N=1, while median request latency rose from 1671 ms to 9242 ms. This shows that increasing offered
concurrency did not produce proportional useful work. It does not measure GPU idle time, batching
decisions, or a root cause.

## Static baseline

Hold arrivals until a batch is full (or a configured timeout expires), then run that batch until all
requests complete. Record time spent waiting for a batch, active work time, completion time, and
idle time.

## Continuous design

At each simulated decode step:

1. retire completed requests;
2. admit queued arrivals that fit the selected batch/token budget;
3. execute one unit of work for every active request;
4. advance simulated time and record queue and active-set state.

Use the same deterministic arrival and request-length trace for both schedulers. The sim models
service units, not GPU kernels, so its throughput units must not be compared directly with the
Phase 1 tokens/s measurement.

## Required measurements

| Metric | Why it is needed |
| --- | --- |
| Busy fraction | Tests the claim that static batching leaves unused service time. |
| Queue wait and completion latency | Shows the cost paid by each request, not only aggregate work. |
| Completed work / simulated time | Compares scheduler efficiency within one model. |
| Active batch size per step | Makes admission behavior inspectable. |

## Measured sim result

**Pending implementation and run.** The result must identify the arrival distribution/seed, request
length trace, capacity, static timeout, and batch/token budget so the comparison is reproducible.
