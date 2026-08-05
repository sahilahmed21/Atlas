# Phase 5.5 — Demo script (90s)

**Status:** Not recorded — this phase depends on real Phase 4 request metrics and a completed Phase 5
counterexample. Do not add a video link until the recording can show those artifacts live.

1. **0–10s — constraint and scope.** State that Atlas measures serving behavior on a laptop/free-tier
   T4 and does not claim multi-node or RDMA deployment. Show the MVP architecture only.
2. **10–40s — real request path.** Start the same load generator used for the experiment. Show request
   arrival, selected replica, route reason, cache signal, TTFT, and tokens/s from the live metric stream.
3. **40–70s — controlled comparison.** Switch either the routing strategy or the predeclared traffic
   trace. Keep model, hardware, generation settings, and time window visible so the metric change is
   interpretable.
4. **70–90s — honest limitation.** Point to the Phase 5 matrix cell where prefix-aware routing loses;
   state the measured metric and linked hypothesis. Close with the documented future-work boundary.

## Recording checklist

- [ ] Link the exact Phase 5 run ids/results used in the recording.
- [ ] Show a clock or request timeline proving metrics are live, not replayed.
- [ ] Redact API keys and user text before publishing.
- [ ] Verify the video has audio/captions and a stable link.

**Video link:** Not recorded.
