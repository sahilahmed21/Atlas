# Phase 5 — Routing experiment (not a confirmation)

**Hardware:** Colab/Kaggle T4 — time-sliced dual vLLM **or** sequential isolated runs  
**Eye-stopper:** Document where the **smart** router **loses**

## Strategies (≥3)

1. Round robin
2. Least-queue / least-load
3. Prefix-aware (route to replica with hottest matching prefix)
4. Optional: random / sticky session

## Traffic patterns

| Pattern | Intent |
| --- | --- |
| High prefix reuse | Shared system prompts / docs |
| Low prefix reuse | Unique prompts |
| Bursty | Poisson / spike arrivals |
| Steady | Constant RPS |

## Honest outcome requirement

- [x] At least one cell where prefix-aware is worse (latency or fairness or cache thrash)
- [x] Hypothesis for why, tested or strongly argued
- [x] Results: `results/phase5/` + `docs/experiments/routing_matrix.md`

**Closed offline** with `worker_mode=simulated`. Live Colab dual-vLLM validation optional. See `ACCEPTANCE.md` + `docs/testing/phase-5.tdd.md`.

## Free-path replica strategy

See `docs/knowledge/hardware-constraints/FREE_PATH_REPLICAS.md`
