# Atlas — Target / Production Architecture

Vision this MVP steps toward. Informed by llm-d, NVIDIA Dynamo, and AIBrix: disaggregated prefill/decode, distributed KV-cache indexer, multi-region Kubernetes, SLO-aware autoscaling.

**Honest scope:** this diagram is the north star. On the free path it is **not** claimed as implemented — Phase 6 states disaggregation / RDMA as informed future work. See [MVP architecture](MVP_ARCHITECTURE.md) for what actually runs on one T4/3050.

Paste into [mermaid.live](https://mermaid.live), a GitHub `.md` fence, or Confluence Mermaid.

## Diagram

```mermaid
flowchart TB
    classDef edge fill:#e0f2fe,stroke:#0369a1,color:#0c4a6e
    classDef gateway fill:#fef3c7,stroke:#b45309,color:#78350f
    classDef control fill:#ede9fe,stroke:#6d28d9,color:#4c1d95
    classDef prefill fill:#fdf4ff,stroke:#a21caf,color:#701a75
    classDef decode fill:#dcfce7,stroke:#15803d,color:#14532d
    classDef cache fill:#fff7ed,stroke:#c2410c,color:#7c2d12
    classDef obs fill:#fee2e2,stroke:#b91c1c,color:#7f1d1d
    classDef infra fill:#f1f5f9,stroke:#475569,color:#1e293b
    classDef research fill:#ecfeff,stroke:#0e7490,color:#164e63

    INT(("Internet")):::edge
    INT --> GW

    subgraph GW["API Gateway"]
        direction TB
        AUTHN["AuthN — API Keys / JWT"]
        AUTHZ["AuthZ — Org Roles"]
        RL["Rate Limiter + Quotas"]
        VAL["OpenAI-Compatible API<br/>/v1/chat/completions"]
        AUTHN --> AUTHZ --> RL --> VAL
    end
    GW:::gateway

    subgraph TEN["Tenant Manager"]
        ORGS[("Organizations, Users, Roles")]
        BILL[("Budgets, Billing, Model Allowlist")]
    end
    GW <--> TEN
    TEN:::control

    subgraph REG["Model Registry"]
        MREG[("name, version, storage location,<br/>memory required, GPU count, quantization")]
    end
    GW --> REG
    REG:::control

    subgraph SCHED["Intelligent Scheduler"]
        direction TB
        EPP["Endpoint Picker<br/>llm-d-style cache scoring"]
        SLO["SLO-Aware Admission<br/>TTFT / latency budget"]
        DISAGG_R["Disaggregated Router<br/>prefill vs decode vs local"]
        EPP --> SLO --> DISAGG_R
    end
    GW --> SCHED
    SCHED:::control

    subgraph PREFILL["Prefill Pool — compute-bound"]
        direction LR
        P1["vLLM / SGLang Prefill Worker"]
        P2["vLLM / SGLang Prefill Worker"]
        P3["... auto-scaled"]
    end
    PREFILL:::prefill

    subgraph DECODE["Decode Pool — memory-bandwidth-bound"]
        direction LR
        D1["vLLM / SGLang Decode Worker"]
        D2["vLLM / SGLang Decode Worker"]
        D3["... auto-scaled"]
    end
    DECODE:::decode

    DISAGG_R -->|"1. route prompt"| PREFILL
    PREFILL -->|"2. KV cache via NIXL/RDMA, non-blocking"| DECODE
    DECODE -->|"3. stream tokens"| GW

    subgraph KVC["Distributed KV Cache Layer"]
        direction TB
        IDX["KV-Cache Indexer<br/>global block-locality index"]
        EVT["KV Events, ZMQ<br/>block create / evict"]
        OFF["Offload Tier<br/>GPU to CPU to Disk/Object Store"]
        EVT --> IDX
        IDX --> OFF
    end
    P1 -.->|"publishes events"| EVT
    D1 -.->|"publishes events"| EVT
    EPP -.->|"queries"| IDX
    KVC:::cache

    subgraph SCALE["Autoscaling"]
        KEDA["KEDA + Workload Variant Autoscaler<br/>triggers: queue depth, KV util, ISL/OSL"]
        HPA["Horizontal Pod Autoscaler"]
        KEDA --> HPA
    end
    HPA -.->|"scales"| PREFILL
    HPA -.->|"scales"| DECODE
    SCALE:::infra

    subgraph K8S["Kubernetes Substrate"]
        GWAPI["Gateway API + Inference Extension"]
        NODES["GPU Node Pools<br/>multi-region, topology-aware"]
    end
    K8S:::infra
    GW -.-> GWAPI
    SCALE -.-> K8S

    subgraph MR["Model Repository"]
        HFHUB[("HF Hub / S3 / Azure Blob / GCS")]
    end
    REG --> MR
    MR:::infra

    subgraph OBS["Observability"]
        PROM["Prometheus"]
        GRAF["Grafana"]
        OTEL["OpenTelemetry Tracing"]
        PROM --> GRAF
        OTEL --> GRAF
    end
    PREFILL -.->|"metrics/traces"| OBS
    DECODE -.->|"metrics/traces"| OBS
    GW -.->|"metrics/traces"| OBS
    OBS:::obs

    subgraph BENCH["Research / Benchmark Harness"]
        AIPERF["aiperf / vllm bench serve"]
        REPORT["TTFT, ITL, Throughput, p95/p99<br/>vs baseline, by routing strategy"]
        AIPERF --> REPORT
    end
    BENCH:::research
    BENCH -.->|"load tests"| GW
    OBS -.->|"feeds"| REPORT
```

## Directory → subsystem (Atlas repo)

Maps the vision onto folders. MVP only implements the free-path subset — see [MVP architecture](MVP_ARCHITECTURE.md).

| Subsystem | Path | First appears |
| --- | --- | --- |
| Memory math / naive baseline | `fundamentals/memory`, `fundamentals/experiments` | Phase 1 |
| Toy allocator / scheduler / prefix | `fundamentals/allocators\|schedulers\|prefix_cache` | Phase 2 |
| OpenAI-compatible gateway | `platform/gateway` | Phase 4 |
| Tenant / keys / quotas | `platform/tenant` | Phase 4 |
| Model registry | `platform/registry` | Phase 4 |
| Prefix-aware / intelligent router | `platform/router` | Phase 4–5 |
| Autoscaling (KEDA later) | `platform/autoscaling` | Phase 4 |
| vLLM workers | `workers/vllm` | Phase 3–4 |
| Benchmarks | `benchmarks/` | Phase 1+ |
| Live dashboard | `dashboard/` | Phase 5.5 |
| Helm / K8s | `deploy/` | Phase 4+ (optional on free path) |

## Scaling rule

- **Do not** invent new top-level folders for features. Extend the table above.
- **Do** keep measured artifacts in `results/phaseN/` and narrative in `docs/`.
- Toy code stays in `fundamentals/`; production path stays in `platform/` + `workers/`. Never merge them into one package.

## Related

- [MVP architecture](MVP_ARCHITECTURE.md)  
- [MVP vs final capability table](MVP_VS_FINAL.md)  
- Research: [llm-d](../research/llm-d/), [DistServe](../research/distserve/), [disaggregated serving](../research/disaggregated-serving/)
