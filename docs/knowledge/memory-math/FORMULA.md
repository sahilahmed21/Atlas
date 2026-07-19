# KV cache memory — Atlas notes

## Core identity

```
KV_bytes ≈ 2 * B * S * L * n_kv * d * bytes_per_elem
```

- `2` = Keys + Values  
- `B` = batch  
- `S` = sequence length (prompt + generated so far)  
- `L` = layers  
- `n_kv` = KV heads (GQA/MQA matters)  
- `d` = head dimension  

## Why concurrent naive HF dies

Each in-flight generate holds its own growing KV. Concurrency multiplies `B` effectively. Without paging + sharing, VRAM cliffs early — Phase 1 measures *where* on *your* card.

## Atlas rule

Always recompute with the **actual** config of the model you load (`num_key_value_heads`, `hidden_size`, `num_hidden_layers`). Do not use Llama-7B blog numbers for a 1B model.
