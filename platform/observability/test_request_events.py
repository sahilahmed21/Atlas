"""Phase 5.5: request event ring (AC-001–002)."""


def test_publish_snapshot_has_route_fields_not_prompt():
    from request_events import RequestEventLog

    log = RequestEventLog(maxlen=10)
    ev = log.publish(
        tenant_id="demo",
        strategy="prefix_aware",
        worker_id="worker-a",
        reason="prefix hit hash=abc ->worker-a",
        cache_signal="hit",
        outcome="ok",
        ttft_ms=12.5,
        completion_ms=40.0,
        tokens_per_s=80.0,
        queue_depth=1.0,
    )

    assert ev.id >= 1
    snap = log.snapshot(limit=10)
    assert len(snap) == 1
    row = snap[0]
    assert row["worker_id"] == "worker-a"
    assert row["strategy"] == "prefix_aware"
    assert row["reason"]
    assert row["cache_signal"] == "hit"
    assert row["ttft_ms"] == 12.5
    assert "prompt" not in row
    assert "messages" not in row
    assert "content" not in row


def test_ring_drops_oldest_when_full():
    from request_events import RequestEventLog

    log = RequestEventLog(maxlen=3)
    for i in range(4):
        log.publish(
            tenant_id="demo",
            strategy="round_robin",
            worker_id=f"w{i}",
            reason=f"r{i}",
            cache_signal="n/a",
            outcome="ok",
            queue_depth=0.0,
        )

    ids = [e["id"] for e in log.snapshot(limit=10)]
    assert len(ids) == 3
    assert ids == sorted(ids)
    assert ids[-1] == 4
