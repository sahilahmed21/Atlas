"""Reliability report: pass@1 vs pass^k with task-level bootstrap CIs, flaky tasks, failure tags,
and per-step cost/latency from the recorder's run log."""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from stats import cluster_bootstrap_ci, pass_at_k, pass_hat_k


def per_task_counts(rows: Sequence[dict[str, Any]]) -> dict[str, tuple[int, int]]:
    """task_id -> (trials n, successes c)."""
    counts: dict[str, list[int]] = {}
    for r in rows:
        n_c = counts.setdefault(r["task_id"], [0, 0])
        n_c[0] += 1
        n_c[1] += int(r["passed"])
    return {t: (n, c) for t, (n, c) in counts.items()}


def per_task_pass_hat_k(rows: Sequence[dict[str, Any]], k: int) -> dict[str, float]:
    return {t: pass_hat_k(n, c, k) for t, (n, c) in per_task_counts(rows).items()}


def _metric(values: list[float], seed: int) -> dict[str, Any]:
    return {"mean": sum(values) / len(values), "ci95": cluster_bootstrap_ci(values, seed=seed)}


def summarize(rows: Sequence[dict[str, Any]], k: int, seed: int = 0) -> dict[str, Any]:
    counts = per_task_counts(rows)
    if not counts:
        raise ValueError("no results")
    if min(n for n, _ in counts.values()) < k:
        raise ValueError(f"every task needs at least k={k} trials")
    at1 = [pass_at_k(n, c, 1) for n, c in counts.values()]
    atk = [pass_at_k(n, c, k) for n, c in counts.values()]
    hatk = [pass_hat_k(n, c, k) for n, c in counts.values()]
    failed = [r for r in rows if not r["passed"]]
    return {
        "tasks": len(counts),
        "k": k,
        "pass_at_1": _metric(at1, seed),
        "pass_at_k": _metric(atk, seed),
        "pass_hat_k": _metric(hatk, seed),
        "flaky_tasks": {t: c for t, (n, c) in sorted(counts.items()) if 0 < c < n},
        "failure_tags": dict(Counter(tag for r in failed for tag in r["tags"])),
    }


async def cost_latency(
    recorder: Any,
    tenant_id: str,
    run_ids: Sequence[str],
    price_in_per_mtok: float = 0.0,
    price_out_per_mtok: float = 0.0,
) -> dict[str, Any]:
    """Aggregate tokens, cost and step latency over recorded runs (summaries only, no content)."""
    steps: list[dict[str, Any]] = []
    for run_id in run_ids:
        run = await recorder.get_run(tenant_id, run_id)
        if run:
            steps.extend(run["steps"])
    prompt = sum(s["prompt_tokens"] or 0 for s in steps)
    completion = sum(s["completion_tokens"] or 0 for s in steps)
    latencies = sorted(s["completion_ms"] for s in steps if s["completion_ms"] is not None)

    def pct(q: float) -> float | None:
        return latencies[min(len(latencies) - 1, int(q * len(latencies)))] if latencies else None

    return {
        "steps": len(steps),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "cost_usd": prompt * price_in_per_mtok / 1e6 + completion * price_out_per_mtok / 1e6,
        "latency_ms": {"p50": pct(0.50), "p95": pct(0.95)},
    }
