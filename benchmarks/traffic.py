"""Deterministic chat traffic traces for Phase 5 routing matrix."""

from __future__ import annotations

from typing import Any

MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
SHARED_SYSTEM = "You are Atlas. Answer briefly using the shared policy context."


def _body(messages: list[dict[str, str]]) -> dict[str, Any]:
    return {"model": MODEL, "messages": messages, "stream": False}


def high_reuse(n: int = 24) -> list[dict[str, Any]]:
    """Same system prefix; unique user turns — affinity should stick."""
    return [
        _body(
            [
                {"role": "system", "content": SHARED_SYSTEM},
                {"role": "user", "content": f"shared-topic question {i}"},
            ]
        )
        for i in range(n)
    ]


def low_reuse(n: int = 24) -> list[dict[str, Any]]:
    """Unique system prefixes — no affinity benefit."""
    return [
        _body(
            [
                {"role": "system", "content": f"Unique policy namespace {i}."},
                {"role": "user", "content": f"unique question {i}"},
            ]
        )
        for i in range(n)
    ]


def steady(n: int = 24) -> list[dict[str, Any]]:
    """Alternating two prefixes — mild reuse."""
    out: list[dict[str, Any]] = []
    for i in range(n):
        sys = "Steady prefix A." if i % 2 == 0 else "Steady prefix B."
        out.append(
            _body(
                [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": f"steady turn {i}"},
                ]
            )
        )
    return out


def bursty(n: int = 24) -> list[dict[str, Any]]:
    """Tight clumps on one hot prefix, then a cold prefix — sticky hotspot risk."""
    out: list[dict[str, Any]] = []
    hot = "Hot burst system prompt."
    cold = "Cold burst system prompt."
    for i in range(n):
        sys = hot if (i % 8) < 6 else cold
        out.append(
            _body(
                [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": f"burst turn {i}"},
                ]
            )
        )
    return out


TRACES = {
    "high_reuse": high_reuse,
    "low_reuse": low_reuse,
    "bursty": bursty,
    "steady": steady,
}


def build_trace(name: str, n: int = 24) -> list[dict[str, Any]]:
    if name not in TRACES:
        raise ValueError(f"unknown traffic pattern: {name}")
    return TRACES[name](n)
