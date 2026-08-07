"""Process-local RPM limiter — NOT production-safe across replicas."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

# Honesty label for HTTP + docs — never call this distributed.
RPM_SCOPE = "process-local"


class ProcessLocalRPMLimiter:
    """Sliding window counter in this process only.

    # ponytail: process-local; shared Redis/platform limiter when multi-replica
    """

    def __init__(
        self,
        window_s: float = 60.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.window_s = window_s
        self._clock = clock or time.monotonic
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _prune(self, tenant_id: str, now: float) -> None:
        cutoff = now - self.window_s
        self._hits[tenant_id] = [t for t in self._hits[tenant_id] if t > cutoff]

    def check(self, tenant_id: str, limit: int) -> bool:
        now = self._clock()
        self._prune(tenant_id, now)
        return len(self._hits[tenant_id]) < limit

    def record(self, tenant_id: str) -> None:
        now = self._clock()
        self._prune(tenant_id, now)
        self._hits[tenant_id].append(now)
