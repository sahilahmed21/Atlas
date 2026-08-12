# Phase 10 — Optional widener (pick one)

**Status:** Not started · **Optional** — do not start until Phase 9 is done  
**Eye-stopper:** Exactly **one** extra artifact that broadens AI-eng JD coverage  
**ACs:** [ACCEPTANCE.md](ACCEPTANCE.md)

## Rule

Phase 10 exists to fill gaps in **general AI engineer** JDs (RAG / eval / cost). It must **not** replace or delay Phases 7–9. Pick **one** track only.

## Tracks (choose one)

### Track A — RAG lane on the same gateway

| Build | Measure |
| --- | --- |
| Minimal retrieve → stuff system prefix → `/v1/chat/completions` | TTFT/cost: cold vs warm shared corpus prefix; hit rate under prefix_aware+gate |

Artifact: `results/phase10-rag/README.md` + small CSV.

### Track B — Eval harness (quality/latency)

| Build | Measure |
| --- | --- |
| Frozen 50-prompt set; scripted runs | p50/p95 TTFT, error rate; optional cheap quality proxy (exact match / judge — label limits) |

Artifact: `results/phase10-eval/`.

### Track C — Cost model

| Build | Measure |
| --- | --- |
| Spreadsheet or script: tokens × latency × hardware hours | ₹ or $ per 1k tokens: naive HF vs vLLM vs routed (labeled assumptions) |

Artifact: `results/phase10-cost/COST_MODEL.md`.

## Forbidden in Phase 10

- Second mega-architecture rewrite
- Fake multi-node
- Claiming production billing
- Starting all three tracks

## Done when

Chosen track has one eye-stopper + inventory update + one resume bullet max.
