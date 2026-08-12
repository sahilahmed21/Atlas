# Phase 9 — Shock package (demo + public narrative)

**Status:** Not started  
**Depends on:** Phase 7 required; Phase 8 strongly preferred  
**Eye-stopper:** Real 90s demo video + README “30-second sell”  
**ACs:** [ACCEPTANCE.md](ACCEPTANCE.md) · Demo runbook base: [phase-5.5/DEMO.md](../phase-5.5/DEMO.md)

## Goal

Package Atlas so a skimmer (recruiter or interviewer) understands the spike in **30 seconds** and a technical interviewer can verify in **90 seconds**.

## Deliverables

### 1. Demo video (required)

Extend Phase 5.5 runbook:

| Beat | Time | Show |
| --- | --- | --- |
| Constraint | 0–10s | Free-path; no RDMA claim; honesty banner |
| Live path | 10–40s | Dashboard: worker, reason, cache, TTFT |
| Comparison | 40–70s | RR vs prefix vs gate (if Phase 8 done) on high_reuse |
| Close | 70–90s | Point at Phase 7 (and 8) CSV/SURPRISE; one honest limit |

**Video link:** only after recording exists — paste into `docs/phases/phase-5.5/DEMO.md` and root README.

### 2. README top sell (required)

Root `README.md` opening block:

1. One Mermaid or link to deep dive
2. One surprise table (GPU numbers from Phase 7; gate from Phase 8 if present)
3. Demo link + “reproduce” one-liner

### 3. Public narrative (required — pick channel)

| Asset | Bar |
| --- | --- |
| Blog or LinkedIn article (~1200–1800 words) | “When prefix-aware routing loses” — cite paths |
| Featured section / pinned repo | Deep dive + pitch + video |

Draft may live at `docs/pitch/PUBLIC_POST.md` before publishing externally.

### 4. Resume bullets refresh (required)

Update `docs/pitch/RESUME_BULLETS.md` and `ONE_PARAGRAPH.md` from claim inventory after 7–8.

## Out of scope

- React rewrite
- New routing strategies
- Phase 10 wideners
- Fake cluster screenshots

## Done when

A stranger can watch the video + skim README and repeat the spike sentence correctly; all links resolve; inventory matches public claims.
