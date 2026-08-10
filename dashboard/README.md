# dashboard/

Phase 5.5 live metrics UI. Served by the gateway at `/dashboard/`.

## Run

```powershell
# terminal 1 — gateway (fake worker via tests/factory, or real workers.yaml URLs)
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080

# browser
# http://127.0.0.1:8080/dashboard/
# Connect with tenant API key (default sk-atlas-demo-key)

# terminal 2 — fire traffic (example)
uv run python -c "from fastapi.testclient import TestClient; print('prefer curl against :8080')"
```

Honesty: numbers come from the gateway request-path event ring (same `observe_request` site as Prometheus). Process-local. Do not invent UI metrics.
