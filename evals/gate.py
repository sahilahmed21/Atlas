"""Regression gate: fail when the candidate's pass^k is credibly lower than the baseline's."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from report import per_task_pass_hat_k
from stats import paired_delta_ci


@dataclass(frozen=True)
class GateResult:
    passed: bool
    delta: float  # mean per-task pass^k, candidate minus baseline
    lo: float
    hi: float


def compare(
    base_rows: Sequence[dict[str, Any]], cand_rows: Sequence[dict[str, Any]], k: int, seed: int = 0
) -> GateResult:
    """Paired by task. Fails only if the whole 95% CI of the delta is below zero (a real drop
    beyond noise), so a noisy re-run of the same model does not trip the gate."""
    base = per_task_pass_hat_k(base_rows, k)
    cand = per_task_pass_hat_k(cand_rows, k)
    if set(base) != set(cand):
        raise ValueError("baseline and candidate must cover the same tasks")
    tasks = sorted(base)
    delta, lo, hi = paired_delta_ci([base[t] for t in tasks], [cand[t] for t in tasks], seed=seed)
    return GateResult(passed=not hi < 0, delta=delta, lo=lo, hi=hi)


async def first_divergence(
    recorder_a: Any, recorder_b: Any, tenant_id: str, run_a: str, run_b: str
) -> int | None:
    """Index of the first step whose request differs between two recorded runs (None = identical).

    Step i's request includes everything the model saw before it, so the first differing hash is
    the step where the two runs' histories parted ways.
    """
    a = await recorder_a.get_run(tenant_id, run_a)
    b = await recorder_b.get_run(tenant_id, run_b)
    if a is None or b is None:
        raise ValueError("unknown run")
    ha = [s["req_hash"] for s in a["steps"]]
    hb = [s["req_hash"] for s in b["steps"]]
    for i, (x, y) in enumerate(zip(ha, hb)):
        if x != y:
            return i
    return None if len(ha) == len(hb) else min(len(ha), len(hb))
