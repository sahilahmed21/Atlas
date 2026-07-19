# Research library index

Paper notes for Atlas. Each folder: `PAPER.md` (citation + claims) + `ATLAS_RELEVANCE.md` (what we implement vs cite vs defer).

| Topic | Folder | Atlas stance |
| --- | --- | --- |
| PagedAttention | [pagedattention/](pagedattention/) | Explain + measure via vLLM; toy sim only |
| DistServe | [distserve/](distserve/) | Future work — informed by network/RDMA limits |
| llm-d | [llm-d/](llm-d/) | Architectural reference for K8s-native serving |
| Prefix cache hierarchy | [prefix-cache-hierarchy/](prefix-cache-hierarchy/) | Router + engine levels |
| Disaggregated serving | [disaggregated-serving/](disaggregated-serving/) | Same as DistServe family — Phase 6 |

## How to add a paper

1. New folder under `docs/research/<slug>/`  
2. Fill citation, year, one-paragraph claim  
3. Explicit: **implement / measure / cite-only / defer**  
4. Link from the phase that needs it
