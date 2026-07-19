# Phase 1 — Naive HF load protocol

## Fixed constants (change only via config)

- Model id + revision: `configs/models/phase1.yaml`
- dtype: fp16 or bf16 (document which)
- `max_new_tokens` sweep: e.g. 32, 128
- concurrency sweep: 1, 2, 4, 8, … until break
- prompt: fixed string (same bytes every run) — see config

## Procedure

1. Cold start: one warmup generate (discard metrics).
2. For each `(n_concurrent, max_new_tokens)`:
   - Reset peak memory stats if CUDA
   - Launch N workers; each runs one generate with same prompt template + unique suffix id
   - Record TTFT (first token if streaming; else full latency as proxy and label it)
   - Record tokens/s, peak VRAM, status (`ok` | `oom` | `error`)
3. Stop sweep after first sustained OOM **or** when p50 latency > 5× the N=1 baseline (latency cliff).
4. Append rows to `results/phase1/naive_load.csv`

## CSV schema

```csv
timestamp,hardware,model,n_concurrent,prompt_tokens,max_new_tokens,ttft_ms,total_ms,tokens_per_s,peak_vram_mb,status,notes
```

## Honest TTFT note

Naive `generate()` without streaming may not expose true TTFT. If so:

- Record `total_ms` as primary
- Set `ttft_ms` empty or equal to `total_ms` and note `ttft_proxy=total` in `notes`
- Phase 3 vLLM will give real TTFT — same load shape still makes the before/after chart valid
