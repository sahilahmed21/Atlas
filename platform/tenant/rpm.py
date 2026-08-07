"""Process-local RPM limiter — NOT production-safe across replicas."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Callable

# Honesty label for HTTP + docs — never call this distributed.
RPM_SCOPE = "process-local"


class ProcessLocalRPMLimiter:
    """Sliding window counter in this process only.

    # ponytail: process-local + threading.Lock; shared store when multi-replica
    Charges on accept (try_acquire), not on upstream success — standard rate-limit.
    """

    def __init__(
        self,
        window_s: float = 60.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.window_s = window_s
        self._clock = clock or time.monotonic
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _prune(self, tenant_id: str, now: float) -> None:
        cutoff = now - self.window_s
        self._hits[tenant_id] = [t for t in self._hits[tenant_id] if t > cutoff]

    def try_acquire(self, tenant_id: str, limit: int) -> bool:
        """Atomically check+record. True if the request may proceed."""
        with self._lock:
            now = self._clock()
            self._prune(tenant_id, now)
            if len(self._hits[tenant_id]) >= limit:
                return False
            self._hits[tenant_id].append(now)
            return True

    def check(self, tenant_id: str, limit: int) -> bool:
        with self._lock:
            now = self._clock()
            self._prune(tenant_id, now)
            return len(self._hits[tenant_id]) < limit

    def record(self, tenant_id: str) -> None:
        with self._lock:
            now = self._clock()
            self._prune(tenant_id, now)
            self._hits[tenant_id].append(now)
