#!/usr/bin/env python3
"""Smoke-check pinned vLLM on WSL/Colab/Kaggle. Exit nonzero on pin mismatch."""

from __future__ import annotations

import sys
from pathlib import Path

# Repo fundamentals on path when run from anywhere
_EXPERIMENTS = Path(__file__).resolve().parents[1] / "fundamentals" / "experiments"
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from vllm_load import PINNED_VLLM_VERSION, assert_runtime_vllm_matches_pin  # noqa: E402


def main() -> int:
    import torch
    import vllm

    assert_runtime_vllm_matches_pin(vllm.__version__)
    print("vllm", vllm.__version__, "(pin ok)", PINNED_VLLM_VERSION)
    print("torch", torch.__version__)
    print("cuda", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("device", torch.cuda.get_device_name(0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
