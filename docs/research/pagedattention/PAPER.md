# PagedAttention

**Citation:** Kwon et al., "Efficient Memory Management for Large Language Model Serving with PagedAttention" (vLLM), SOSP 2023.  
**Link:** https://arxiv.org/abs/2309.06180

## Core claim

KV cache managed like virtual memory (blocks + block table) → higher batch size / less waste than contiguous allocation.

## Claims to verify against Phase 1–3

- [ ] **Phase 2 measurement required:** a controlled contiguous-reservation simulation shows more
  tail waste or fragmentation than the paged simulation under the same variable-length trace.
  Phase 1's +73.7 MB peak-memory difference is an aggregate GPU metric, so it does not prove
  contiguous-KV waste by itself.
- [ ] **Phase 3 measurement required:** a pinned vLLM run improves the comparable load curve on
  specified hardware. Do not substitute the paper's benchmark for Atlas's own result.
