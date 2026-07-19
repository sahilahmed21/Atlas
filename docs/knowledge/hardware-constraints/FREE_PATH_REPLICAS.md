# Free-path hardware constraints

| Device | VRAM | Role |
| --- | --- | --- |
| Laptop 3050 | ~4GB | Toys, tiny HF, gateway dev |
| Colab/Kaggle T4 | 16GB | vLLM, Phase 3/5 experiments |

## Multi-replica without multi-GPU

1. **Time-sliced:** two vLLM processes, `gpu_memory_utilization≈0.4` each  
2. **Sequential conditions:** run strategy A session, save CSV, then strategy B — often cleaner science  

Router logic does not need physical separation — only distinct worker endpoints + cache/load signals.

## Framing

₹0 + real curves beats rented A100 with shallow understanding. Constraint survives into Phase 6 future-work wording.
