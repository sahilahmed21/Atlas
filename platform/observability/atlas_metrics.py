"""Request-path Prometheus metrics for Phase 4 / 5.5."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


class AtlasMetrics:
    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry or CollectorRegistry()
        self.requests = Counter(
            "atlas_requests_total",
            "Chat completion requests handled by the gateway",
            ["tenant", "strategy", "worker_id", "outcome"],
            registry=self.registry,
        )
        self.cache = Counter(
            "atlas_cache_signals_total",
            "Prefix-cache route signals (local map only)",
            ["cache_signal"],
            registry=self.registry,
        )
        self.ttft = Histogram(
            "atlas_ttft_ms",
            "Time to first token/chunk in milliseconds",
            ["worker_id"],
            registry=self.registry,
            buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000),
        )
        self.completion = Histogram(
            "atlas_completion_ms",
            "End-to-end completion time in milliseconds",
            ["worker_id"],
            registry=self.registry,
            buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 5000, 30000),
        )
        self.tokens = Histogram(
            "atlas_tokens_per_s",
            "Tokens per second when usage is present",
            ["worker_id"],
            registry=self.registry,
            buckets=(1, 5, 10, 25, 50, 100, 200, 500),
        )
        self.queue_depth = Gauge(
            "atlas_queue_depth",
            "In-flight gateway requests (process-local)",
            registry=self.registry,
        )

    def queue_inc(self) -> None:
        self.queue_depth.inc()

    def queue_dec(self) -> None:
        self.queue_depth.dec()

    def observe_request(
        self,
        *,
        tenant_id: str,
        strategy: str,
        worker_id: str,
        outcome: str,
        cache_signal: str = "n/a",
        ttft_ms: float | None = None,
        completion_ms: float | None = None,
        tokens_per_s: float | None = None,
    ) -> None:
        self.requests.labels(
            tenant=tenant_id,
            strategy=strategy,
            worker_id=worker_id,
            outcome=outcome,
        ).inc()
        self.cache.labels(cache_signal=cache_signal).inc()
        if ttft_ms is not None:
            self.ttft.labels(worker_id=worker_id).observe(ttft_ms)
        if completion_ms is not None:
            self.completion.labels(worker_id=worker_id).observe(completion_ms)
        if tokens_per_s is not None:
            self.tokens.labels(worker_id=worker_id).observe(tokens_per_s)
