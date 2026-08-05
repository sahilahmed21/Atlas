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

**Pending implementation and run.** Do not fill this section from the Phase 1 GPU peak.

Required artifact: a deterministic variable-length trace in `results/phase2/` containing, for both
designs, request id, requested/used tokens, reserved bytes, used bytes, free bytes, allocation
outcome, and fragmentation/waste metric.

Acceptance:

1. Run both designs on exactly the same trace and block size.
2. Show the contiguous-reservation waste and any fragmentation-induced allocation failure.
3. Show paged allocated-vs-used bytes and explain the block-size trade-off.
4. State explicitly which result is simulated and which Phase 1 result is measured.
