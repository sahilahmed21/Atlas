# Phase 4 — Platform layer (router centerpiece)

**Hardware:** Laptop for API; Colab for GPU-backed integration tests  
**Reuse:** Achira / FDRYZE patterns for gateway, tenants, observability

## Components

| Component | Path | MVP depth |
| --- | --- | --- |
| FastAPI OpenAI-compatible gateway | `platform/gateway` | `/v1/chat/completions` + streaming |
| Tenant manager | `platform/tenant` | API keys, RPM quota |
| Model registry | `platform/registry` | YAML → registry objects |
| Observability | `platform/observability` | Prometheus metrics + OTEL hooks |
| Autoscaling | `platform/autoscaling` | Queue-depth metric; KEDA YAML sketch |
| **Router** | `platform/router` | **Round robin vs prefix-aware** |

## Steps

### 4.1 Gateway skeleton
### 4.2 Tenant + keys
### 4.3 Registry
### 4.4 Worker client (vLLM OpenAI server)
### 4.5 Router strategies (disproportionate effort)
### 4.6 Metrics export for dashboard (5.5)

## Novel piece

Only the **prefix-aware router** needs to be "yours." Everything else should be thin and boring.
