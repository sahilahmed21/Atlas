# PagedAttention — concept (not reimplementation)

**Idea:** Store KV in fixed-size blocks (pages); map logical token positions → physical blocks via a block table — like virtual memory.

**Why Atlas cares:** Explains Phase 1 waste; your Phase 2 allocator sim; Phase 3 source reading.

**What Atlas will not do on free path:** Reimplement CUDA PagedAttention kernels. Evaluate and explain; measure vLLM.

See also: [`../../research/pagedattention/`](../../research/pagedattention/)
