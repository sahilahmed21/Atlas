# platform/

Phase 4+. Production path. Workers stay ignorant of tenants; gateway + tenant + router own that.

Router is the centerpiece — keep gateway/tenant boring.

## Scaffold (Phase 4)

| Path | Role |
| --- | --- |
| `gateway/app.py` | FastAPI `POST /v1/chat/completions` |
| `tenant/tenants.py` | YAML tenants + API-key auth |
| `registry/workers_registry.py` | YAML workers + resolve-by-model |
| `router/strategies.py` | round_robin / least_load / prefix_aware |

```powershell
# tests (fake worker; no GPU)
uv run pytest platform workers -q

# run gateway (needs real worker URLs in configs/models/workers.yaml)
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080
```
