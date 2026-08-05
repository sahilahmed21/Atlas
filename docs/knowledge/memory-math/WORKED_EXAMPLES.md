# Worked examples log

| Model | h | L | n_kv | d | dtype | Example (B,S) | KV GiB | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TinyLlama-1.1B-Chat-v1.0 | 2048 | 22 | 4 | 64 | fp16 | (4, 2048) | 0.172 | Phase 1 (abandoned: OOM at load on 3050) |
| TinyLlama-1.1B-Chat-v1.0 | 2048 | 22 | 4 | 64 | fp16 | (8, 4096) | 0.688 | Phase 1 (abandoned: OOM at load on 3050) |
| Qwen2.5-0.5B-Instruct | 896 | 24 | 2 | 64 | fp16 | (4, 2048) | 0.094 | Phase 1 |
| Qwen2.5-0.5B-Instruct | 896 | 24 | 2 | 64 | fp16 | (8, 4096) | 0.375 | Phase 1 |

Add a row every time you change models.
