# MVP vs final

Diagrams: [MVP](MVP_ARCHITECTURE.md) · [Target / production](TARGET_ARCHITECTURE.md)

| Capability | MVP (Phases 1–3 + thin 4) | Final (Phases 4–6 + north star) |
| --- | --- | --- |
| Memory math | Yes | Referenced in write-up |
| Naive HF concurrent load | Yes | Baseline chart |
| Toy paged / continuous / prefix | Yes | Diffed vs vLLM |
| Real vLLM | Yes (Colab) | Workers wrap it |
| OpenAI `/v1/chat/completions` | Stub optional → required in 4 | Required |
| Multi-tenant keys / quotas | Phase 4 simple | Orgs, roles, budgets |
| Prefix-aware router | Phase 4–5 centerpiece | + SLO admission, disagg router |
| Time-sliced dual replicas | Yes (free path) | Multi-node pools |
| Live dashboard | Phase 5.5 | Grafana + OTEL |
| K8s / Helm / KEDA | Optional sketch | Full substrate |
| Disaggregation / RDMA KV | No | Target only (Phase 6 future work) |

## Non-goals for free path

- Simultaneous physical multi-GPU
- Claiming production SLA / HA
- Training or fine-tuning pipelines
- Calling time-sliced processes “DistServe”
