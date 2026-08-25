# Phase 9 — Run the service + record the demo

**Status:** Recording shipped — [docs/demo/atlas-demo.mp4](../../demo/atlas-demo.mp4) (also linked from root README).  
**Goal:** 90s video that sells **mechanics + honesty**, not a fake live TTFT win.

**Cite on screen (end card):**  
`results/phase5/SURPRISE.md` (sim ~2×) · `results/phase5-live/SURPRISE_GPU.md` (WEAKENED) · `results/phase8/BEFORE_AFTER.md` (gate recovers sim; live TTFT win **not** confirmed)

**API key (demo only):** `sk-atlas-demo-key`

---

## A. Run the service (laptop — recommended for recording)

You need **3 terminals**: stub worker A, stub worker B, gateway. Then a 4th for load (or run load between takes).

### A0. Once

```powershell
cd C:\projects\Atlas
uv sync
```

### A1. Stub workers (no GPU)

Save is optional — paste into two terminals, change port:

**Terminal 1 — worker-a `:8001`**

```powershell
cd C:\projects\Atlas
uv run python -c @"
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
app = FastAPI()
@app.get('/healthz')
def h(): return {'ok': True}
@app.post('/v1/chat/completions')
def chat(body: dict):
    return JSONResponse({
        'id': 'chatcmpl-stub-a', 'object': 'chat.completion',
        'model': body.get('model', 'stub'),
        'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'ok'}, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 8, 'completion_tokens': 4, 'total_tokens': 12},
    })
uvicorn.run(app, host='127.0.0.1', port=8001)
"@
```

**Terminal 2 — worker-b `:8002`** — same script, `port=8002`, `chatcmpl-stub-b`.

Confirm `configs/models/workers.yaml` points at `http://127.0.0.1:8001/v1` and `...8002/v1` (default).

> Stubs prove **routing + dashboard**. For GPU TTFT on screen, use §C (Colab) instead — still cut to CSV for the close.

### A2. Gateway

**Terminal 3**

`--app-dir platform/gateway` alone is **not enough** — `app.py` imports basename modules from sibling dirs (`atlas_metrics`, `tenants`, `strategies`, …). Pytest sets those via `pyproject.toml`; uvicorn does not. Set `PYTHONPATH` first:

```powershell
cd C:\projects\Atlas
$env:PYTHONPATH = @(
  "platform\gateway",
  "platform\tenant",
  "platform\registry",
  "platform\router",
  "platform\observability",
  "workers"
) -join ";"
$env:ATLAS_STRATEGY = "prefix_aware"
$env:ATLAS_PREFIX_LOAD_MARGIN = "0"   # sticky first (gate off)
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080
```

Open: http://127.0.0.1:8080/dashboard/  
Click **Connect** (key prefilled). Honesty banner must be visible.

### A3. Drive realistic load (for the request log)

**Terminal 4** — prefer the paced mixer (jitter + mixed prefixes). The old zero-delay
`high_reuse` loop looks like a metronome on the dashboard.

```powershell
cd C:\projects\Atlas
$env:PYTHONPATH = "benchmarks"
uv run python benchmarks/demo_load.py --mix realistic --n 40 --mean-ms 160 --jitter-ms 110
```

Dashboard should fill with **HIT / MISS / GATE** badges, **several** prefix hashes in
Detail, mixed workers, and ~50–300 ms spacing — not a perfect A/B toggle.

**Why A/B happens:** `ATLAS_PREFIX_LOAD_MARGIN=1` + one shared system prompt makes the
gate alternate hit/gate forever (served pressure). Use `--mix realistic` (default), not
`--mix sticky` / raw `high_reuse`, when you want the log to look like clients.

For a pure sticky take (gate off), use `--mix sticky`. For hotspot clumps: `--mix bursty`.
Gate-focused but still interleaved: `--mix gated`.

<details>
<summary>Old one-liner (still works; looks synthetic on the log)</summary>

```powershell
cd C:\projects\Atlas
$env:PYTHONPATH = "C:\projects\Atlas\benchmarks"
uv run python -c @"
import json, urllib.request
from traffic import high_reuse
BASE='http://127.0.0.1:8080'
KEY='sk-atlas-demo-key'
for i, body in enumerate(high_reuse(24)):
    req = urllib.request.Request(
        BASE + '/v1/chat/completions',
        data=json.dumps(body).encode(),
        headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        print(i, r.headers.get('x-atlas-worker-id'), r.headers.get('x-atlas-cache-signal'), r.headers.get('x-atlas-route-reason', '')[:60])
"@
```
</details>

### A4. Show the gate (second take / mid-video restart)

Stop gateway (Ctrl+C). Restart with gate on:

```powershell
cd C:\projects\Atlas
$env:PYTHONPATH = @(
  "platform\gateway",
  "platform\tenant",
  "platform\registry",
  "platform\router",
  "platform\observability",
  "workers"
) -join ";"
$env:ATLAS_STRATEGY = "prefix_aware"
$env:ATLAS_PREFIX_LOAD_MARGIN = "1"
uv run uvicorn app:create_app_from_env --factory --app-dir platform/gateway --port 8080
```

Reconnect dashboard → hard-refresh the page → re-run `demo_load.py --mix realistic`.  
Look for **GATE** badges / `gate: sticky break …` in Detail, **multiple** prefixes, and
both workers used — not miss → gate → hit → gate on a single hash.

### A5. Optional: round_robin contrast

```powershell
$env:ATLAS_STRATEGY = "round_robin"
$env:ATLAS_PREFIX_LOAD_MARGIN = "0"
# restart gateway, reconnect, re-run load — workers should alternate
```

---

## B. Perfect 90s demo script (what to say + show)

Record **1080p**, browser + terminal visible, mic clear. Do **one rehearsal** dry.

| Time | Say | Show |
| --- | --- | --- |
| **0–10s** | “Atlas: multi-tenant LLM serving behavior on free-path GPUs — laptop 3050 + Colab T4. Not multi-node, not RDMA.” | Dashboard honesty banner + URL bar `localhost:8080/dashboard` |
| **10–35s** | “Live request path: same events as Prometheus. high_reuse traffic, prefix_aware, gate off.” | Connect → run load → table: one worker, miss→hit, clock ticking |
| **35–55s** | “Sticky affinity works — high hit rate, skew to one replica. That’s the failure mode production gates for.” | Zoom worker column + cache column |
| **55–75s** | “Enable load gate. Breaks stickiness when the warm replica is hot — `hit_broken`, load spreads.” | Restart with `ATLAS_PREFIX_LOAD_MARGIN=1`, reload, both workers |
| **75–90s** | “Sim: sticky ~2× worse TTFT, gate recovers. Live T4: affinity pattern holds; large cliff **WEAKENED**; gate **mechanics** confirmed, live TTFT win **not** claimed this run. Paths on screen.” | Flash `SURPRISE.md` / `SURPRISE_GPU.md` / `BEFORE_AFTER.md` (3s each) or one slide |

### Do / don’t

| Do | Don’t |
| --- | --- |
| Label stubs if no GPU: “routing demo; TTFT from CSV” | Imply stub TTFT is Phase 7 GPU |
| End on WEAKENED + mechanics | “Gate made live TTFT 2× faster” |
| Show live clock moving | Replay a static screenshot as “live” |
| Keep key as `sk-atlas-demo-key` only | Paste real secrets |

---

## C. Optional Colab (GPU authenticity)

1. Dual vLLM `:8001` / `:8002` per `docs/runbooks/COLAB_KAGGLE.md` + Phase 7 RUN_LOG  
2. Point `workers.yaml` (or tunnel) at those URLs  
3. Same gateway + dashboard + load script  
4. Still close with committed CSVs — one Colab take can be noisy (Phase 7 vs 8 variance)

---

## D. Recording checklist (Phase 9 AC)

- [ ] Honesty banner readable  
- [ ] Live clock proves not a screenshot  
- [ ] Sticky (margin 0) then gated (margin 1) both shown  
- [ ] End card cites the three result paths  
- [ ] No real API secrets; no user PII  
- [x] Upload / commit recording → root README + this file  
- [ ] Captions or clear VO (optional follow-up)

**Video:** [docs/demo/atlas-demo.mp4](../../demo/atlas-demo.mp4)

---

## E. After the take

1. Paste video URL here and in root README  
2. Refresh `docs/pitch/ONE_PARAGRAPH.md` + `RESUME_BULLETS.md` from claim inventory  
3. Optional: `docs/pitch/PUBLIC_POST.md`  
4. Tick Phase 9 ACCEPTANCE.md  

Reproduce matrices anytime:

```powershell
uv run python benchmarks/run_routing_matrix.py --n 24
uv run python benchmarks/run_routing_matrix.py --phase8 --n 24
```
