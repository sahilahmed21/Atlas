# fundamentals/

Phases 1–2. Toy sims and naive baselines. Never import tenant/auth code here.

| Path | Phase |
| --- | --- |
| `memory/` | 1 helpers (optional formula scripts) |
| `experiments/` | 1 naive HF load + plot |
| `allocators/` | 2 contiguous vs paged |
| `schedulers/` | 2 static vs continuous |
| `prefix_cache/` | 2 token-id prefix hash |

```powershell
uv run pytest fundamentals/allocators fundamentals/schedulers fundamentals/prefix_cache
uv run python fundamentals/allocators/allocator_sim.py
uv run python fundamentals/schedulers/scheduler_sim.py
uv run python fundamentals/prefix_cache/prefix_cache_sim.py
```
