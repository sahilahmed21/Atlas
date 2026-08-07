"""Pinned vLLM version helper — matches Phase 3 pin."""

from __future__ import annotations

PINNED_VLLM_VERSION = "0.26.0"


def assert_worker_vllm_matches_pin(reported: str) -> None:
    if reported != PINNED_VLLM_VERSION:
        raise RuntimeError(
            f"worker vLLM {reported!r} does not match pin {PINNED_VLLM_VERSION}"
        )
