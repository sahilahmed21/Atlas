"""Guards Phase 3 naive-vs-vLLM overlay joining (not pixel drawing)."""

from pathlib import Path

import pytest

HEADER = (
    "timestamp,hardware,model,n_concurrent,prompt_tokens,max_new_tokens,"
    "ttft_ms,total_ms,tokens_per_s,peak_vram_mb,status,notes\n"
)


def write_csv(path: Path, body: str) -> Path:
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def test_pair_by_concurrency_aligns_ok_rows(tmp_path):
    from plot_naive_vs_vllm import pair_by_concurrency

    naive = write_csv(
        tmp_path / "naive.csv",
        "t,hw,m,1,23,32,1000,1000,19.1,969.2,ok,\n"
        "t,hw,m,2,23,32,2000,2000,12.2,988.3,ok,\n",
    )
    vllm = write_csv(
        tmp_path / "vllm.csv",
        "t,hw,m,1,23,32,400,400,40.0,800.0,ok,vllm=0.26.0\n"
        "t,hw,m,2,23,32,500,500,35.0,820.0,ok,vllm=0.26.0\n",
    )

    pairs = pair_by_concurrency(naive, vllm, max_new_tokens=32)

    assert [p["n_concurrent"] for p in pairs] == [1, 2]
    assert pairs[0]["naive_total_ms"] == 1000.0
    assert pairs[0]["vllm_total_ms"] == 400.0
    assert pairs[0]["naive_hardware"] == "hw"
    assert pairs[0]["vllm_hardware"] == "hw"


def test_pair_by_concurrency_skips_points_missing_on_one_side(tmp_path):
    from plot_naive_vs_vllm import pair_by_concurrency

    naive = write_csv(
        tmp_path / "naive.csv",
        "t,hw,m,1,23,32,1000,1000,19.1,969.2,ok,\n"
        "t,hw,m,8,23,32,9000,9000,3.4,1042.9,ok,\n",
    )
    vllm = write_csv(
        tmp_path / "vllm.csv",
        "t,hw,m,1,23,32,400,400,40.0,800.0,ok,vllm=0.26.0\n",
    )

    pairs = pair_by_concurrency(naive, vllm, max_new_tokens=32)

    assert [p["n_concurrent"] for p in pairs] == [1]


def test_missing_vllm_csv_raises(tmp_path):
    from plot_naive_vs_vllm import pair_by_concurrency

    naive = write_csv(
        tmp_path / "naive.csv",
        "t,hw,m,1,23,32,1000,1000,19.1,969.2,ok,\n",
    )
    missing = tmp_path / "does_not_exist.csv"

    with pytest.raises(FileNotFoundError):
        pair_by_concurrency(naive, missing, max_new_tokens=32)


def test_overlay_title_labels_cross_hardware():
    from plot_naive_vs_vllm import overlay_title

    title = overlay_title(
        "Qwen/Qwen2.5-0.5B-Instruct",
        naive_hardware="laptop-3050",
        vllm_hardware="colab-t4",
    )

    assert "laptop-3050" in title
    assert "colab-t4" in title
    assert "cross-hardware" in title


def test_overlay_title_same_hardware_has_no_cross_warning():
    from plot_naive_vs_vllm import overlay_title

    title = overlay_title("m", naive_hardware="colab-t4", vllm_hardware="colab-t4")

    assert "colab-t4" in title
    assert "cross-hardware" not in title


def test_plot_writes_png(tmp_path):
    from plot_naive_vs_vllm import pair_by_concurrency, plot_overlay

    naive = write_csv(
        tmp_path / "naive.csv",
        "t,laptop-3050,Qwen/Qwen2.5-0.5B-Instruct,1,23,32,1000,1000,19.1,969.2,ok,\n"
        "t,laptop-3050,Qwen/Qwen2.5-0.5B-Instruct,2,23,32,2000,2000,12.2,988.3,ok,\n",
    )
    vllm = write_csv(
        tmp_path / "vllm.csv",
        "t,colab-t4,Qwen/Qwen2.5-0.5B-Instruct,1,23,32,400,400,40.0,800.0,ok,vllm=0.26.0\n"
        "t,colab-t4,Qwen/Qwen2.5-0.5B-Instruct,2,23,32,500,500,35.0,820.0,ok,vllm=0.26.0\n",
    )
    out = tmp_path / "naive_vs_vllm.png"
    pairs = pair_by_concurrency(naive, vllm, max_new_tokens=32)

    path = plot_overlay(pairs, out, model="Qwen/Qwen2.5-0.5B-Instruct")

    assert path == out
    assert out.is_file()
    assert out.stat().st_size > 0
    assert pairs[0]["naive_hardware"] == "laptop-3050"
    assert pairs[0]["vllm_hardware"] == "colab-t4"


def test_gitignore_models_rule_is_repo_root_only():
    """Bare `models/` also ignores configs/models/; pin must be `/models/`."""
    root = Path(__file__).resolve().parents[2]
    lines = [
        line.strip()
        for line in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert "/models/" in lines
    assert "models/" not in lines
