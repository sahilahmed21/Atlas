# Phase 1 — Memory math

**Model under study:** Qwen/Qwen2.5-0.5B-Instruct  
_(Switched from TinyLlama-1.1B: fp16 weights ~2.05 GiB OOMed on RTX 3050 4GB at load — CUDA warmup + display overhead left insufficient headroom.)_  
**Hidden size `h`:** 896  
**Layers `L`:** 24  
**Query heads `n_q`:** 14  
**KV heads `n_kv`:** 2  _(GQA: not equal to query heads)_  
**Head dim `d`:** 64  _(h / n_q)_  
**dtype bytes `b`:** 2 (fp16)  
**Device VRAM:** 4.0 GiB (RTX 3050 Laptop)

## Formula (derive, don't memorize)

For **one** request with prompt+generated length `S` tokens, batch size `B`:

```
KV_bytes ≈ 2 * B * S * L * n_kv * d * b
           ↑
           K and V
```

If the model uses MQA/GQA, use `n_kv` not `n_q`.

**Qwen2.5-0.5B substitute:**

```
KV_bytes = 2 * B * S * 24 * 2 * 64 * 2
         = B * S * 12288

KV_GiB   = (12288 * B * S) / 1024³
```

**Weights:** `~0.49e9 * b ≈ 0.91 GiB` (inference only; ignore optimizer).

**Activations (rough):** ~0.5 GiB headroom for Phase 1 (activations + CUDA fragmentation + temp tensors). Refine later if measured.

**Total ≈ weights + KV + activations + fragmentation**

### Hand check (B=4, S=2048)

```
KV_bytes = 12288 * 4 * 2048 = 100_663_296 ≈ 0.094 GiB
Total    ≈ 0.91 + 0.094 + 0.50 = 1.50 GiB  (< 4.0 → fits)
```

## Worked table (fill ≥3 rows)

| B | S | KV GiB | Weights GiB | Est. total GiB | Device VRAM | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 512 | 0.006 | 0.91 | 1.42 | 4.0 | fits |
| 1 | 2048 | 0.024 | 0.91 | 1.43 | 4.0 | fits |
| 4 | 2048 | 0.094 | 0.91 | 1.50 | 4.0 | fits |
| 8 | 4096 | 0.375 | 0.91 | 1.79 | 4.0 | fits |

_Note: pure KV math says all rows fit; naive concurrent `generate()` may still cliff via activations / fragmentation / thread contention — that is what the load sweep measures._

## Predictions before running

1. First combo I expect to OOM: `B=8, S=4096` (or high N in the concurrent sweep before pure KV exceeds VRAM)
2. Why (one sentence): Weights leave ~3 GiB free, but concurrent HF generates stack activations + fragmentation; OOM may still appear before the KV formula alone predicts it.
3. Latency collapse before OOM? **Yes** — naive concurrent `generate()` is expected to serialize / thrash under memory pressure, so p50 latency should climb well before a hard OOM.

## Link to experiment

After runs, mark which predictions were wrong in [`RUN_LOG.md`](RUN_LOG.md). Wrong predictions are more valuable than lucky ones.
