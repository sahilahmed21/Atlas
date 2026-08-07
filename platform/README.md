# platform/

Phase 4+. Production path. Workers stay ignorant of tenants; gateway + tenant + router own that.

Router is the centerpiece — keep gateway/tenant boring.

## Scaffold (Phase 4 — done offline)

| Path | Role |
| --- | --- |
| `gateway/app.py` | FastAPI `POST /v1/chat/completions` + RPM + `/metrics` |
| `tenant/tenants.py` + `rpm.py` | YAML tenants + process-local RPM |
| `registry/workers_registry.py` | YAML workers + resolve-by-model |
| `router/strategies.py` | round_robin / least_load / prefix_aware |
| `observability/` | Prometheus + OTEL hooks |

```powershell
uv run pytest platform workers -q
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080
```

`x-atlas-rpm-scope: process-local` — not multi-replica safe. KEDA sketch: `deploy/keda/atlas-queue-depth.yaml` (planning only).
