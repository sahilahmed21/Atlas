"""Routing strategies — round_robin / least_load / prefix_aware."""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class RouteDecision:
    worker_id: str
    strategy: str
    reason: str
    cache_signal: str = "n/a"


def prefix_hash(prompt: str) -> str:
    # ponytail: full-prompt hash; real APC uses block-aligned prefixes — Phase 5
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _require_workers(workers: Sequence[Any]) -> None:
    if not workers:
        raise ValueError("no eligible workers")


class RoundRobinRouter:
    def __init__(self) -> None:
        self._i = 0
        self._lock = threading.Lock()

    def choose(self, workers: Sequence[Any], **_: Any) -> RouteDecision:
        _require_workers(workers)
        with self._lock:
            w = workers[self._i % len(workers)]
            self._i += 1
        return RouteDecision(
            worker_id=w.id,
            strategy="round_robin",
            reason=f"round_robin index->{w.id}",
            cache_signal="n/a",
        )


class LeastLoadRouter:
    def choose(
        self,
        workers: Sequence[Any],
        loads: dict[str, int] | None = None,
        **_: Any,
    ) -> RouteDecision:
        _require_workers(workers)
        loads = loads or {}
        best = min(workers, key=lambda w: (loads.get(w.id, 0), w.id))
        load = loads.get(best.id, 0)
        return RouteDecision(
            worker_id=best.id,
            strategy="least_load",
            reason=f"least_load load={load} ->{best.id}",
            cache_signal="n/a",
        )


class PrefixAwareRouter:
    def choose(
        self,
        workers: Sequence[Any],
        prompt: str = "",
        prefix_owners: dict[str, str] | None = None,
        **_: Any,
    ) -> RouteDecision:
        _require_workers(workers)
        owners = prefix_owners or {}
        key = prefix_hash(prompt)
        owner = owners.get(key)
        by_id = {w.id: w for w in workers}
        if owner and owner in by_id:
            return RouteDecision(
                worker_id=owner,
                strategy="prefix_aware",
                reason=f"prefix hit hash={key} ->{owner}",
                cache_signal="hit",
            )
        fallback = sorted(workers, key=lambda w: w.id)[0]
        return RouteDecision(
            worker_id=fallback.id,
            strategy="prefix_aware",
            reason=f"prefix miss hash={key}; fallback ->{fallback.id}",
            cache_signal="miss",
        )


def build_router(strategy: str):
    if strategy == "round_robin":
        return RoundRobinRouter()
    if strategy == "least_load":
        return LeastLoadRouter()
    if strategy == "prefix_aware":
        return PrefixAwareRouter()
    raise ValueError(f"unknown strategy: {strategy}")
