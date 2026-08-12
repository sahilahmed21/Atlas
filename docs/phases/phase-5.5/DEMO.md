# Phase 5.5 — Demo script (90s)

**Status:** App ready — video not recorded yet.

## Live demo runbook (laptop)

1. Start gateway with dual fake/sim workers (or point `configs/models/workers.yaml` at real OpenAI-compatible endpoints).
2. Open `http://127.0.0.1:8080/dashboard/` — click **Connect** with `sk-atlas-demo-key`.
3. Fire load (same traces as Phase 5): high_reuse then switch `ATLAS_STRATEGY` / restart with `prefix_aware` vs `round_robin`.
4. Show live clock, worker column, cache hit/miss, TTFT bars, route reason.
5. Close with Phase 5 surprise cell (`results/phase5/SURPRISE.md`): prefix-aware can win hits and lose latency.

```powershell
cd C:\projects\Atlas
$env:ATLAS_STRATEGY = "prefix_aware"
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080
```

For a one-process demo without real GPUs, inject `SimulatedWorkerClient` the same way tests/harness do (factory), or run chat completions against any OpenAI-compatible stub on 8001/8002.

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

**Video link:** Not recorded — tracking moved to **Phase 9** (`docs/phases/phase-9/`). Use this runbook when recording.
