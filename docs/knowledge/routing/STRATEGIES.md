# Routing strategies (Atlas)

| Strategy | Signal | Expected win | Expected loss |
| --- | --- | --- | --- |
| Round robin | none | Fair, simple | Ignores cache |
| Least load | queue depth | Smooth latency | Ignores prefix |
| Prefix-aware | prefix hash → replica | High reuse traffic | Low reuse / imbalance |
| Sticky session | session id | Multi-turn KV | Uneven load |

Experiment matrix: `docs/experiments/routing_matrix.md`
