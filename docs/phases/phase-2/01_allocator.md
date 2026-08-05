# Phase 2 — Allocator notes

## What F1 looked like in Phase 1

At N=1→8, measured peak GPU allocation rose from 969.2 MB to 1042.9 MB (+73.7 MB), while the
KV formula for seven additional ~55-token requests predicts +4.5 MiB. That metric contains
weights, activations, allocator state, and KV cache; it is not evidence that HuggingFace allocated
a contiguous KV tensor or that fragmentation caused the gap. It is the reason to isolate those
effects in a deterministic simulation.

## Naive design

Represent each request as one contiguous reservation sized for its declared maximum sequence
length. Track:

- reserved tokens and bytes;
- used tokens and bytes;
- unused tail bytes (`reserved - used`);
- allocation failure when no contiguous free span is large enough, even if the sum of free spans is
  sufficient.

Use the Qwen Phase 1 KV rate of 12,288 bytes/token for the byte conversion, but keep the allocator
itself model-agnostic by accepting `bytes_per_token`.

## Paged design

Split each request's logical KV tokens into fixed-size blocks. Allocate a physical block only when
the sequence grows into it and retain a per-request block table from logical block index to physical
block index. Report at most one partially occupied block per active sequence as internal tail waste.

This is a teaching model of the allocation property described by
[PagedAttention](https://arxiv.org/abs/2309.06180), not its CUDA attention kernel or vLLM block
manager.

## Measured sim result

**Simulated** (not Phase 1 GPU). Trace: `DEFAULT_TRACE` in `fundamentals/allocators/allocator_sim.py`
(`bytes_per_token=12288`, `block_size=16`).

| Design | Total used bytes | Total reserved bytes | Total waste bytes |
| --- | --- | --- | --- |
| Contiguous | 28,041,216 | 77,045,760 | **49,004,544** |
| Paged | 28,041,216 | 28,483,584 | **442,368** |

Paged waste is ~1% of contiguous waste on this trace because contiguous reserves each
request's `max_len` while paged reserves `ceil(used/16)*16` tokens.

Artifact: `results/phase2/allocator.csv`  
Reproduce: `uv run python fundamentals/allocators/allocator_sim.py`  
Tests: `uv run pytest fundamentals/allocators`

**Phase 1 measured** peak VRAM (+73.7 MB) remains an aggregate GPU metric and is **not**
explained by this table.
