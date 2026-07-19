# Phase 1 — Failure curve (eye-stopper)

## Chart checklist

- [ ] X-axis: concurrency (or seq length) — labeled
- [ ] Y-axis: latency (ms) and/or tokens/s — labeled
- [ ] OOM points marked distinctly (or second panel: peak VRAM)
- [ ] Hardware + model in title
- [ ] Data file path in caption: `results/phase1/naive_load.csv`
- [ ] Image saved: `results/phase1/oom_latency_curve.png`

## Caption template

> Naive HuggingFace `generate()` on **[hardware]** with **[model]**. Latency collapses / OOM at **N=…** (or S=…). This matches / contradicts the Phase 1 memory prediction that KV would exceed VRAM at **…**.

## Embed

Link or paste image here after generation:

`results/phase1/oom_latency_curve.png`
