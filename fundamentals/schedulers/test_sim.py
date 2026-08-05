"""Phase 2.2 — static vs continuous scheduler guarantees (TDD)."""

from sim import (
    CAPACITY,
    DEFAULT_TRACE,
    STATIC_BATCH,
    STATIC_TIMEOUT,
    run_continuous,
    run_static,
)


def test_static_and_continuous_complete_all_requests():
    static = run_static(DEFAULT_TRACE)
    continuous = run_continuous(DEFAULT_TRACE)
    assert static["completed"] == len(DEFAULT_TRACE)
    assert continuous["completed"] == len(DEFAULT_TRACE)


def test_continuous_busy_fraction_at_least_static_on_default_trace():
    static = run_static(DEFAULT_TRACE)
    continuous = run_continuous(DEFAULT_TRACE)
    assert continuous["busy_fraction"] >= static["busy_fraction"]
    assert static["params"]["capacity"] == CAPACITY
    assert static["params"]["batch_size"] == STATIC_BATCH
    assert static["params"]["timeout"] == STATIC_TIMEOUT
