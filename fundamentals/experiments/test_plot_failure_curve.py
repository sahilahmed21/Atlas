"""Guards the failure classification behind the Phase 1 curve.

Drawing is not tested; deciding which points are failures is.
"""

from pathlib import Path

from plot_failure_curve import load_runs, mark_failures

HEADER = (
    "timestamp,hardware,model,n_concurrent,prompt_tokens,max_new_tokens,"
    "ttft_ms,total_ms,tokens_per_s,peak_vram_mb,status,notes\n"
)


def write_csv(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "naive_load.csv"
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def test_load_runs_sorts_by_concurrency_and_parses_numbers(tmp_path):
    csv_path = write_csv(
        tmp_path,
        "t,hw,m,4,23,32,4000,4000,7.2,1001.8,ok,\n"
        "t,hw,m,1,23,32,1000,1000,19.1,969.2,ok,\n",
    )

    runs = load_runs(csv_path)

    assert [r["n_concurrent"] for r in runs] == [1, 4]
    assert runs[0]["total_ms"] == 1000.0
    assert runs[1]["peak_vram_mb"] == 1001.8


def test_oom_row_is_marked_even_without_timings(tmp_path):
    csv_path = write_csv(
        tmp_path,
        "t,hw,m,1,23,32,1000,1000,19.1,969.2,ok,\n"
        "t,hw,m,8,23,32,,,,1042.9,oom,\n",
    )

    runs = mark_failures(load_runs(csv_path))

    assert runs[0]["failure"] is None
    assert runs[1]["failure"] == "oom"


def test_latency_cliff_is_measured_against_the_n1_baseline(tmp_path):
    csv_path = write_csv(
        tmp_path,
        "t,hw,m,1,23,32,1000,1000,19.1,969.2,ok,\n"
        "t,hw,m,2,23,32,2000,2000,12.2,988.3,ok,\n"
        "t,hw,m,8,23,32,9000,9000,3.4,1042.9,ok,\n",
    )

    runs = mark_failures(load_runs(csv_path), cliff_factor=5.0)

    assert [r["failure"] for r in runs] == [None, None, "cliff"]


def test_no_baseline_means_no_cliff_claim(tmp_path):
    """Without an N=1 row we cannot honestly call anything a cliff."""
    csv_path = write_csv(tmp_path, "t,hw,m,4,23,32,9000,9000,3.4,1001.8,ok,\n")

    runs = mark_failures(load_runs(csv_path))

    assert runs[0]["failure"] is None
