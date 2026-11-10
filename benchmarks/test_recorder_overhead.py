"""Smoke test: the overhead benchmark runs and reports sane, ordered percentiles."""

import asyncio


def test_overhead_benchmark_reports_live_and_record_percentiles(tmp_path):
    from recorder_overhead import measure

    result = asyncio.run(measure(tmp_path, concurrent_runs=5, steps=2))

    for mode in ("live", "record"):
        row = result[mode]
        assert row["requests"] == 10
        assert 0 < row["p50_ms"] <= row["p95_ms"] <= row["max_ms"]
    assert "added_p50_ms" in result and "added_p95_ms" in result
