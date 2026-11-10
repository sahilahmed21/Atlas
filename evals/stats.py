"""Reliability statistics for agent evals: pass@k, pass^k and bootstrap confidence intervals.

n trials per task, c successes: pass@k = P(at least one of k sampled trials succeeds),
pass^k = P(all k sampled trials succeed) (tau-bench's reliability metric). Both use the unbiased
combinatorial estimators over the n observed trials. Tasks, not trials, are the unit of
resampling, because trials of one task are not independent samples of the task population.
"""

from __future__ import annotations

import math
import random
from typing import Sequence


def _check(n: int, c: int, k: int) -> None:
    if not (1 <= k <= n) or not (0 <= c <= n):
        raise ValueError(f"need 1 <= k <= n and 0 <= c <= n (got n={n}, c={c}, k={k})")


def pass_at_k(n: int, c: int, k: int) -> float:
    _check(n, c, k)
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    _check(n, c, k)
    if c < k:
        return 0.0
    return math.comb(c, k) / math.comb(n, k)


def cluster_bootstrap_ci(
    per_task: Sequence[float], seed: int = 0, n_boot: int = 2000, alpha: float = 0.05
) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean over tasks (resampling tasks with replacement)."""
    if not per_task:
        raise ValueError("no tasks")
    rng = random.Random(seed)
    n = len(per_task)
    means = sorted(sum(per_task[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return lo, hi


def paired_delta_ci(
    base: Sequence[float], cand: Sequence[float], seed: int = 0, n_boot: int = 2000
) -> tuple[float, float, float]:
    """(mean delta, lo, hi) of candidate minus baseline, paired by task."""
    if len(base) != len(cand):
        raise ValueError("baseline and candidate must cover the same tasks")
    diffs = [c - b for b, c in zip(base, cand)]
    lo, hi = cluster_bootstrap_ci(diffs, seed=seed, n_boot=n_boot)
    return sum(diffs) / len(diffs), lo, hi
