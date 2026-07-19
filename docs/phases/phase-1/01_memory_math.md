# Phase 1 — Memory math

**Model under study:** _(fill)_  
**Hidden size `h`:** _(fill)_  
**Layers `L`:** _(fill)_  
**KV heads `n_kv`:** _(fill)_  _(GQA: may differ from query heads)_  
**Head dim `d`:** _(fill)_  
**dtype bytes `b`:** 2 for fp16/bf16, 1 for fp8, etc.

## Formula (derive, don't memorize)

For **one** request with prompt+generated length `S` tokens, batch size `B`:

```
KV_bytes ≈ 2 * B * S * L * n_kv * d * b
           ↑
           K and V
```

If the model uses MQA/GQA, use `n_kv` not `n_q`.

**Weights:** from `model.num_parameters() * b` (ignore optimizer — inference only).

**Activations (rough):** order-of-magnitude; for Phase 1, treat as "extra headroom" — note if you refine later.

**Total ≈ weights + KV + activations + fragmentation**

## Worked table (fill ≥3 rows)

| B | S | KV GiB | Weights GiB | Est. total GiB | Device VRAM | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 512 | | | | | |
| 1 | 2048 | | | | | |
| 4 | 2048 | | | | | |
| 8 | 4096 | | | | | |

## Predictions before running

1. First combo I expect to OOM: `B=_, S=_`
2. Why (one sentence): _
3. Latency collapse before OOM? Yes/No — reason: _

## Link to experiment

After runs, mark which predictions were wrong in [`RUN_LOG.md`](RUN_LOG.md). Wrong predictions are more valuable than lucky ones.
