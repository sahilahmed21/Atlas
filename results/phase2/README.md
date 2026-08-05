# results/phase2/

Simulated metrics (CPU toys). Not GPU measurements.

| File | Toy | Reproduce |
| --- | --- | --- |
| `allocator.csv` | Contiguous vs paged | `uv run python fundamentals/allocators/allocator_sim.py` |
| `scheduler.csv` | Static vs continuous | `uv run python fundamentals/schedulers/scheduler_sim.py` |
| `prefix_cache.csv` | Shared vs unique prefixes | `uv run python fundamentals/prefix_cache/prefix_cache_sim.py` |

Tests: `uv run pytest fundamentals/allocators fundamentals/schedulers fundamentals/prefix_cache`
