"""RED/GREEN: request-path Prometheus metrics (AC-011)."""

from prometheus_client import CollectorRegistry, generate_latest


def test_observe_request_emits_labeled_metrics():
    from atlas_metrics import AtlasMetrics

    reg = CollectorRegistry()
    m = AtlasMetrics(registry=reg)
    m.queue_inc()
    m.observe_request(
        tenant_id="demo",
        strategy="prefix_aware",
        worker_id="worker-b",
        outcome="ok",
        cache_signal="hit",
        ttft_ms=12.5,
        completion_ms=40.0,
        tokens_per_s=80.0,
    )
    m.queue_dec()

    text = generate_latest(reg).decode("utf-8")
    assert "atlas_requests_total" in text
    assert 'tenant="demo"' in text
    assert 'strategy="prefix_aware"' in text
    assert 'worker_id="worker-b"' in text
    assert 'outcome="ok"' in text
    assert "atlas_queue_depth" in text
    assert "atlas_ttft_ms" in text
    assert "atlas_completion_ms" in text
    assert "atlas_tokens_per_s" in text
    assert 'cache_signal="hit"' in text


def test_queue_depth_gauge_tracks_inflight():
    from atlas_metrics import AtlasMetrics

    reg = CollectorRegistry()
    m = AtlasMetrics(registry=reg)
    m.queue_inc()
    m.queue_inc()
    text = generate_latest(reg).decode("utf-8")
    assert "atlas_queue_depth 2.0" in text or "atlas_queue_depth 2" in text
    m.queue_dec()
    text2 = generate_latest(reg).decode("utf-8")
    assert "atlas_queue_depth 1.0" in text2 or "atlas_queue_depth 1" in text2
