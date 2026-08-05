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

**Simulated** (CPU ticks). Trace: `DEFAULT_TRACE` in `fundamentals/schedulers/sim.py`
(`capacity=4`, static `batch_size=4`, `timeout=5`).

| Design | Busy ticks | Idle ticks | Busy fraction | Mean completion latency (ticks) | Work completed |
| --- | --- | --- | --- | --- | --- |
| Static | (see CSV) | (see CSV) | **0.3846** | **13.50** | 56 |
| Continuous | (see CSV) | (see CSV) | **0.5417** | **7.00** | 56 |

Continuous keeps a higher busy fraction and lower mean completion latency on this staggered
arrival pattern because it admits work at step boundaries instead of waiting for a full batch
or timeout.

Artifact: `results/phase2/scheduler.csv`  
Reproduce: `uv run python fundamentals/schedulers/sim.py`  
Tests: `uv run pytest fundamentals/schedulers`

These busy-fraction units are **not** Phase 1 tokens/s (27.7 at N=8).
