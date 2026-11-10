"""RED/GREEN Phase 13: pass@k / pass^k estimators and bootstrap CIs, checked against hand values."""

import math

import pytest

from stats import cluster_bootstrap_ci, paired_delta_ci, pass_at_k, pass_hat_k


def test_pass_at_k_matches_hand_computed_values():
    assert pass_at_k(n=8, c=4, k=1) == pytest.approx(0.5)
    assert pass_at_k(n=4, c=2, k=2) == pytest.approx(1 - 1 / 6)  # 1 - C(2,2)/C(4,2)
    assert pass_at_k(n=5, c=0, k=3) == 0.0
    assert pass_at_k(n=5, c=5, k=3) == 1.0
    assert pass_at_k(n=5, c=3, k=3) == 1.0  # fewer than k failures: some pick must succeed


def test_pass_hat_k_is_the_probability_all_k_trials_succeed():
    assert pass_hat_k(n=8, c=6, k=3) == pytest.approx(math.comb(6, 3) / math.comb(8, 3))  # 20/56
    assert pass_hat_k(n=4, c=2, k=2) == pytest.approx(1 / 6)
    assert pass_hat_k(n=5, c=2, k=3) == 0.0  # fewer than k successes
    assert pass_hat_k(n=5, c=5, k=5) == 1.0


def test_pass_hat_k_never_exceeds_pass_at_k_and_k1_agree():
    for n in range(1, 9):
        for c in range(n + 1):
            assert pass_hat_k(n, c, 1) == pytest.approx(pass_at_k(n, c, 1)) == pytest.approx(c / n)
            for k in range(1, n + 1):
                assert pass_hat_k(n, c, k) <= pass_at_k(n, c, k) + 1e-12


def test_k_larger_than_trials_is_rejected():
    with pytest.raises(ValueError):
        pass_hat_k(n=3, c=2, k=4)
    with pytest.raises(ValueError):
        pass_at_k(n=3, c=2, k=0)


def test_bootstrap_ci_is_deterministic_and_brackets_the_mean():
    values = [1.0, 0.0, 1.0, 1.0, 0.5, 0.0, 1.0, 0.75]
    mean = sum(values) / len(values)

    lo, hi = cluster_bootstrap_ci(values, seed=7)

    assert (lo, hi) == cluster_bootstrap_ci(values, seed=7)
    assert lo <= mean <= hi and 0.0 <= lo < hi <= 1.0


def test_bootstrap_ci_collapses_when_every_task_agrees_and_narrows_with_more_tasks():
    assert cluster_bootstrap_ci([1.0] * 10, seed=1) == (1.0, 1.0)

    few = cluster_bootstrap_ci([1.0, 0.0] * 4, seed=1)
    many = cluster_bootstrap_ci([1.0, 0.0] * 100, seed=1)
    assert (many[1] - many[0]) < (few[1] - few[0])


def test_paired_delta_ci_detects_a_real_drop_and_not_noise():
    base = [1.0] * 20
    worse = [1.0] * 10 + [0.0] * 10  # candidate clearly regressed on half the tasks
    delta, lo, hi = paired_delta_ci(base, worse, seed=3)
    assert delta == pytest.approx(-0.5) and hi < 0  # CI excludes zero on the negative side

    delta, lo, hi = paired_delta_ci(base, list(base), seed=3)
    assert (delta, lo, hi) == (0.0, 0.0, 0.0)

    noisy_base = [1.0, 0.0] * 10
    noisy_cand = [0.0, 1.0] * 10  # same mean, different tasks
    delta, lo, hi = paired_delta_ci(noisy_base, noisy_cand, seed=3)
    assert delta == 0.0 and lo < 0 < hi
