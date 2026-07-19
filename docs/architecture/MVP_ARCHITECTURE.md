# Atlas — MVP Architecture

Single free-tier GPU (Colab/Kaggle T4 or RTX 3050), multi-tenant FastAPI gateway, prefix-aware routing, offline `fundamentals/` proof-of-understanding module.

**Constraint:** production-grade multi-tenant LLM serving behavior on constrained hardware — not multi-node / RDMA.

Paste the diagram into [mermaid.live](https://mermaid.live), a GitHub `.md` fence, or Confluence Mermaid.

## Diagram

```mermaid
flowchart TB
    classDef client fill:#e0f2fe,stroke:#0369a1,color:#0c4a6e
    classDef gateway fill:#fef3c7,stroke:#b45309,color:#78350f
    classDef control fill:#ede9fe,stroke:#6d28d9,color:#4c1d95
    classDef infer fill:#dcfce7,stroke:#15803d,color:#14532d
    classDef obs fill:#fee2e2,stroke:#b91c1c,color:#7f1d1d
    classDef fund fill:#f1f5f9,stroke:#475569,color:#1e293b

    U["Client / Load Test Script<br/>vllm bench serve or aiperf"]:::client

    subgraph GW["API Gateway — FastAPI"]
        direction TB
        AUTH["API Key / JWT Auth"]
        RATE["Per-Tenant Rate Limiter"]
        VALID["Request Validation<br/>OpenAI-compatible schema"]
        STREAM["SSE Streaming Passthrough"]
        AUTH --> RATE --> VALID --> STREAM
    end
    U -->|"POST /v1/chat/completions"| GW
    GW:::gateway

    subgraph TEN["Tenant Manager"]
        PG[("Postgres<br/>orgs, api_keys, quotas, allowed_models")]
    end
    GW <-->|"check quota, auth"| TEN
    TEN:::control

    subgraph RTR["Router / Scheduler"]
        direction TB
        HASH["Prefix Hasher<br/>hash(prompt prefix)"]
        SCORE["Cache-Aware Scorer<br/>mimics llm-d Endpoint Picker"]
        RR["Round-Robin Fallback"]
        HASH --> SCORE
    end
    GW --> RTR
    RTR:::control

    subgraph GPU["Single Free-Tier GPU — Colab/Kaggle T4 or RTX 3050"]
        direction LR
        subgraph R1["vLLM Replica A<br/>gpu_memory_utilization = 0.4"]
            M1["Qwen2.5-1.5B or Llama-3.2-3B, 4-bit"]
            KV1[("Paged KV Cache Blocks")]
        end
        subgraph R2["vLLM Replica B<br/>gpu_memory_utilization = 0.4"]
            M2["Same model, separate process"]
            KV2[("Paged KV Cache Blocks")]
        end
    end
    SCORE -->|"route by cache score"| R1
    SCORE -->|"route by cache score"| R2
    RR -.->|"fallback path"| R1
    RR -.->|"fallback path"| R2
    GPU:::infer

    subgraph OBS["Observability"]
        PROM["Prometheus<br/>scrapes /metrics: queue depth, KV util"]
        GRAF["Grafana Dashboard<br/>TTFT, throughput, cache hit rate"]
        PROM --> GRAF
    end
    R1 -->|"/metrics"| PROM
    R2 -->|"/metrics"| PROM
    GW -->|"/metrics"| PROM
    OBS:::obs

    subgraph FUND["/fundamentals — offline, standalone proof of understanding"]
        direction TB
        F1["Naive vs Paged Allocator Simulator"]
        F2["Static vs Continuous Batching Simulator"]
        F3["Prefix-Hash Cache Simulator"]
        F4["Naive HF baseline — the break-point run"]
    end
    FUND:::fund
    FUND -.->|"informs design of"| RTR
    FUND -.->|"informs design of"| GPU
```

## Repo mapping

| Diagram box | Path |
| --- | --- |
| API Gateway | `platform/gateway/` |
| Tenant Manager | `platform/tenant/` |
| Router / Scheduler | `platform/router/` |
| vLLM replicas | `workers/vllm/` |
| Observability | `platform/observability/` + `dashboard/` |
| Fundamentals | `fundamentals/` |

## Related

- [Target / production architecture](TARGET_ARCHITECTURE.md) — what this MVP steps toward  
- [MVP vs final capability table](MVP_VS_FINAL.md)
