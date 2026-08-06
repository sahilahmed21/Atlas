"""Offline contract tests for the Phase 3 vLLM load harness (no GPU)."""

from pathlib import Path

import pytest


def test_csv_fields_match_phase1():
    from naive_hf_load import CSV_FIELDS as PHASE1_FIELDS
    from vllm_load import CSV_FIELDS

    assert CSV_FIELDS == PHASE1_FIELDS


def test_build_row_embeds_pinned_vllm_version():
    from vllm_load import PINNED_VLLM_VERSION, build_row

    row = build_row(
        hardware="colab-t4",
        model="Qwen/Qwen2.5-0.5B-Instruct",
        n_concurrent=1,
        prompt_tokens=23,
        max_new_tokens=32,
        ttft_ms=100.0,
        total_ms=400.0,
        tokens_per_s=40.0,
        peak_vram_mb=800.0,
        status="ok",
        notes="ttft_proxy=total",
    )

    assert row["n_concurrent"] == 1
    assert row["status"] == "ok"
    assert f"vllm={PINNED_VLLM_VERSION}" in row["notes"]
    assert PINNED_VLLM_VERSION == "0.26.0"


def test_assert_runtime_vllm_matches_pin():
    from vllm_load import assert_runtime_vllm_matches_pin

    assert_runtime_vllm_matches_pin("0.26.0")
    with pytest.raises(RuntimeError, match="0.26.0"):
        assert_runtime_vllm_matches_pin("0.25.0")


def test_load_phase3_config_requires_same_revision_keys(tmp_path):
    from vllm_load import load_config

    path = tmp_path / "phase3.yaml"
    path.write_text(
        "hub_model_id: Qwen/Qwen2.5-0.5B-Instruct\n"
        "revision: 7ae557604adf67be50417f59c2c2f167def9a775\n"
        "dtype: float16\n"
        "prompt_template: hello\n"
        "max_new_tokens_sweep: [32]\n"
        "concurrency_sweep: [1, 2, 4, 8]\n"
        "cliff_factor: 5.0\n"
        "hardware_label: colab-t4\n"
        "vllm_version: '0.26.0'\n",
        encoding="utf-8",
    )

    cfg = load_config(path)

    assert cfg["revision"].startswith("7ae5576")
    assert cfg["concurrency_sweep"] == [1, 2, 4, 8]
    assert cfg["vllm_version"] == "0.26.0"
