# KV cache — conceptual map

## What it stores

Per layer, per token position: key and value tensors used so decode does not re-encode past tokens.

## What goes wrong without management

- Contiguous pre-allocation for max_S wastes VRAM  
- No cross-request sharing of common prefixes  
- Fragmentation under variable lengths  

## Atlas split

| Layer | Where |
| --- | --- |
| Math + failure | Phase 1 docs + results |
| Toy paging | `fundamentals/allocators` |
| Real engine | vLLM (Phase 3) |
| Routing that *uses* cache affinity | `platform/router` (Phase 4–5) |
