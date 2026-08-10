"""Process-local request event ring for Phase 5.5 live dashboard."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RequestEvent:
    id: int
    ts: float
    tenant_id: str
    strategy: str
    worker_id: str
    reason: str
    cache_signal: str
    outcome: str
    ttft_ms: float | None
    completion_ms: float | None
    tokens_per_s: float | None
    queue_depth: float

    def as_public_dict(self) -> dict[str, Any]:
        # Explicit allowlist — never include prompt/messages/content
        return asdict(self)


class RequestEventLog:
    """Bounded FIFO of request-path events.

    # ponytail: process-local only; multi-replica fan-in needs a bus later
    """

    def __init__(self, maxlen: int = 256) -> None:
        self._buf: deque[RequestEvent] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._next_id = 1

    def publish(
        self,
        *,
        tenant_id: str,
        strategy: str,
        worker_id: str,
        reason: str,
        cache_signal: str,
        outcome: str,
        ttft_ms: float | None = None,
        completion_ms: float | None = None,
        tokens_per_s: float | None = None,
        queue_depth: float = 0.0,
    ) -> RequestEvent:
        with self._cv:
            ev = RequestEvent(
                id=self._next_id,
                ts=time.time(),
                tenant_id=tenant_id,
                strategy=strategy,
                worker_id=worker_id,
                reason=reason,
                cache_signal=cache_signal,
                outcome=outcome,
                ttft_ms=ttft_ms,
                completion_ms=completion_ms,
                tokens_per_s=tokens_per_s,
                queue_depth=queue_depth,
            )
            self._next_id += 1
            self._buf.append(ev)
            self._cv.notify_all()
            return ev

    def snapshot(self, *, limit: int = 50, after: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            rows = [e for e in self._buf if e.id > after]
            if limit >= 0:
                rows = rows[-limit:]
            return [e.as_public_dict() for e in rows]

    def wait_after(self, after: int, *, timeout: float = 1.0) -> list[RequestEvent]:
        """Block until a newer event exists or timeout; return events with id > after."""
        deadline = time.monotonic() + timeout
        with self._cv:
            while True:
                newer = [e for e in self._buf if e.id > after]
                if newer:
                    return list(newer)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return []
                self._cv.wait(timeout=remaining)
