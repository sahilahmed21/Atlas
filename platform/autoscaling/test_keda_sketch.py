"""RED/GREEN: KEDA sketch presence + vLLM pin helper (AC-013)."""

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_keda_sketch_queries_atlas_queue_depth():
    path = ROOT / "deploy" / "keda" / "atlas-queue-depth.yaml"
    assert path.is_file(), "KEDA sketch missing"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["kind"] == "ScaledObject"
    triggers = doc["spec"]["triggers"]
    assert triggers[0]["type"] == "prometheus"
    query = triggers[0]["metadata"]["query"]
    assert "atlas_queue_depth" in query
    # honesty: sketch must not claim it was applied
    text = path.read_text(encoding="utf-8")
    assert "sketch" in text.lower() or "planning" in text.lower()


def test_assert_worker_vllm_matches_pin():
    from vllm_pin import PINNED_VLLM_VERSION, assert_worker_vllm_matches_pin

    assert PINNED_VLLM_VERSION == "0.26.0"
    assert_worker_vllm_matches_pin("0.26.0")
    with pytest.raises(RuntimeError, match="0.26.0"):
        assert_worker_vllm_matches_pin("0.25.0")
