"""Routing strategies — round_robin / least_load / prefix_aware."""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class RouteDecision:
    worker_id: str
    strategy: str
    reason: str
    cache_signal: str = "n/a"


def prefix_hash(prompt: str) -> str:
    # ponytail: not block-aligned APC — upgrade when wiring real vLLM cache events
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _msg_field(message: Any, name: str) -> str:
    if isinstance(message, Mapping):
        return str(message.get(name, "") or "")
    return str(getattr(message, name, "") or "")


def shared_prefix_key(messages: Sequence[Any] | str) -> str:
    """Hash shared prefix only (first system, else first message)."""
    if isinstance(messages, str):
        return prefix_hash(messages)
    if not messages:
        return prefix_hash("")
    for message in messages:
        if _msg_field(message, "role") == "system":
            return prefix_hash(f"system:{_msg_field(message, 'content')}")
    first = messages[0]
    role = _msg_field(first, "role")
    content = _msg_field(first, "content")
    return prefix_hash(f"{role}:{content}")


def _require_workers(workers: Sequence[Any]) -> None:
    if not workers:
        raise ValueError("no eligible workers")


def _least_load_worker(workers: Sequence[Any], loads: dict[str, int]) -> Any:
    return min(workers, key=lambda w: (loads.get(w.id, 0), w.id))


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
        best = _least_load_worker(workers, loads)
        load = loads.get(best.id, 0)
        return RouteDecision(
            worker_id=best.id,
            strategy="least_load",
            reason=f"least_load load={load} ->{best.id}",
            cache_signal="n/a",
        )


class PrefixAwareRouter:
    def __init__(self, load_margin: int = 0) -> None:
        # ponytail: margin 0 = gate off (Phase 5/7 sticky repro); set >=1 for Phase 8
        self.load_margin = max(0, int(load_margin))

    def choose(
        self,
        workers: Sequence[Any],
        prompt: str = "",
        prefix_key: str = "",
        prefix_owners: dict[str, str] | None = None,
        loads: dict[str, int] | None = None,
        **_: Any,
    ) -> RouteDecision:
        _require_workers(workers)
        owners = prefix_owners or {}
        loads = loads or {}
        key = prefix_key or prefix_hash(prompt)
        owner = owners.get(key)
        by_id = {w.id: w for w in workers}
        if owner and owner in by_id:
            if self.load_margin > 0:
                owner_load = loads.get(owner, 0)
                alt = _least_load_worker(workers, loads)
                alt_load = loads.get(alt.id, 0)
                if owner_load >= alt_load + self.load_margin and alt.id != owner:
                    return RouteDecision(
                        worker_id=alt.id,
                        strategy="prefix_aware",
                        reason=(
                            f"prefix hit broken by load_gate "
                            f"load={owner_load} vs alt={alt_load} "
                            f"margin={self.load_margin} ->{alt.id}"
                        ),
                        cache_signal="hit_broken",
                    )
            return RouteDecision(
                worker_id=owner,
                strategy="prefix_aware",
                reason=f"prefix hit hash={key} ->{owner}",
                cache_signal="hit",
            )
        claim = _least_load_worker(workers, loads)
        return RouteDecision(
            worker_id=claim.id,
            strategy="prefix_aware",
            reason=f"prefix miss hash={key}; least_load claim ->{claim.id}",
            cache_signal="miss",
        )


def build_router(strategy: str, load_margin: int = 0):
    if strategy == "round_robin":
        return RoundRobinRouter()
    if strategy == "least_load":
        return LeastLoadRouter()
    if strategy == "prefix_aware":
        return PrefixAwareRouter(load_margin=load_margin)
    raise ValueError(f"unknown strategy: {strategy}")
