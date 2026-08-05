"""Phase 2.1 — contiguous vs paged allocator guarantees (TDD)."""

from __future__ import annotations

from allocator_sim import (
    BYTES_PER_TOKEN,
    BLOCK_SIZE,
    DEFAULT_TRACE,
    run_contiguous,
    run_paged,
    summarize,
)


def test_contiguous_reserves_max_len_and_wastes_unused_tail():
    rows = run_contiguous(DEFAULT_TRACE, bytes_per_token=BYTES_PER_TOKEN)
    first = rows[0]
    # DEFAULT_TRACE[0] = (max_len=512, used=40)
    assert first["reserved_tokens"] == 512
    assert first["used_tokens"] == 40
    assert first["waste_bytes"] == (512 - 40) * BYTES_PER_TOKEN
    assert first["outcome"] == "ok"


def test_paged_allocates_ceil_used_over_block_and_bounds_tail_waste():
    rows = run_paged(DEFAULT_TRACE, bytes_per_token=BYTES_PER_TOKEN, block_size=BLOCK_SIZE)
    first = rows[0]
    # used=40, block=16 → 3 blocks → 48 reserved tokens
    assert first["reserved_tokens"] == 48
    assert first["used_tokens"] == 40
    assert first["waste_bytes"] == (48 - 40) * BYTES_PER_TOKEN
    assert first["waste_bytes"] <= BLOCK_SIZE * BYTES_PER_TOKEN
    assert first["outcome"] == "ok"


def test_paged_total_waste_is_less_than_contiguous_on_default_trace():
    contig = summarize(run_contiguous(DEFAULT_TRACE))
    paged = summarize(run_paged(DEFAULT_TRACE))
    assert paged["total_waste_bytes"] < contig["total_waste_bytes"]
    assert paged["total_used_bytes"] == contig["total_used_bytes"]
