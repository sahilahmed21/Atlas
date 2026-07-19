# DistServe → Atlas

| Action | Status |
| --- | --- |
| Implement | **Defer** (Phase 6 future work) |
| Understand interference argument | Required for honest pitch |
| Fake with two processes on one GPU | **Forbidden** as a DistServe claim |

**Phase 6 wording:** With multi-node + RDMA-class interconnect, disaggregate prefill/decode per DistServe; on single T4, interference still exists but cannot be scheduled away by topology.
