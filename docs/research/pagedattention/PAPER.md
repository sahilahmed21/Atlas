# PagedAttention

**Citation:** Kwon et al., "Efficient Memory Management for Large Language Model Serving with PagedAttention" (vLLM), SOSP 2023.  
**Link:** https://arxiv.org/abs/2309.06180

## Core claim

KV cache managed like virtual memory (blocks + block table) → higher batch size / less waste than contiguous allocation.

## Claims to verify against Phase 1–3

- [ ] Contiguous allocation waste visible on our failure curve  
- [ ] vLLM improves concurrency before OOM on same hardware  
