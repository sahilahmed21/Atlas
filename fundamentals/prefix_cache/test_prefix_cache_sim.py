"""Phase 2.3 — token-id prefix cache guarantees (TDD)."""

from prefix_cache_sim import (
    SHARED_PREFIX_LEN,
    run_cache,
    shared_prefix_traffic,
    unique_prefix_traffic,
)


def test_shared_prefix_traffic_gets_hits_after_first_miss():
    summary = run_cache(shared_prefix_traffic(n=8))
    assert summary["hits"] == 7
    assert summary["misses"] == 1
    assert summary["avoided_prefill_tokens"] == 7 * SHARED_PREFIX_LEN
    assert summary["full_prefill_tokens"] == SHARED_PREFIX_LEN + sum(
        len(p) - SHARED_PREFIX_LEN for p in shared_prefix_traffic(n=8)
    )


def test_unique_prefix_traffic_has_zero_hits():
    summary = run_cache(unique_prefix_traffic(n=8))
    assert summary["hits"] == 0
    assert summary["misses"] == 8
    assert summary["avoided_prefill_tokens"] == 0
