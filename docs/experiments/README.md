# Experiment registry

| ID | Phase | Question | Artifact |
| --- | --- | --- | --- |
| E1 | 1 | Where does naive HF collapse on our hardware? | `results/phase1/` |
| E2 | 3 | How does vLLM change that curve? | `results/phase3/` |
| E3 | 5 | When does prefix-aware routing lose? | `results/phase5/` + [routing_matrix.md](routing_matrix.md) |

Rules: one question per experiment; change one variable at a time when possible; log hardware + versions.
