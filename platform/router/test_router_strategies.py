"""RED/GREEN: round_robin / least_load / prefix_aware + reasons (AC-005, AC-006)."""

from types import SimpleNamespace


def _workers():
    return [
        SimpleNamespace(id="worker-a", model="m", base_url="http://a/v1"),
        SimpleNamespace(id="worker-b", model="m", base_url="http://b/v1"),
        SimpleNamespace(id="worker-c", model="m", base_url="http://c/v1"),
    ]


def test_round_robin_cycles_and_emits_reason():
    from strategies import RoundRobinRouter

    router = RoundRobinRouter()
    workers = _workers()
    picks = [router.choose(workers).worker_id for _ in range(4)]

    assert picks == ["worker-a", "worker-b", "worker-c", "worker-a"]
    decision = router.choose(workers)
    assert decision.strategy == "round_robin"
    assert decision.reason


def test_least_load_picks_lowest_and_emits_reason():
    from strategies import LeastLoadRouter

    router = LeastLoadRouter()
    workers = _workers()
    loads = {"worker-a": 5, "worker-b": 1, "worker-c": 3}

    decision = router.choose(workers, loads=loads)

    assert decision.worker_id == "worker-b"
    assert decision.strategy == "least_load"
    assert "load" in decision.reason.lower() or "1" in decision.reason


def test_prefix_aware_routes_to_owner_on_hit():
    from strategies import PrefixAwareRouter, prefix_hash

    router = PrefixAwareRouter()
    workers = _workers()
    prompt = "You are a helpful assistant.\nUser: hi"
    owners = {prefix_hash(prompt): "worker-b"}

    decision = router.choose(workers, prompt=prompt, prefix_owners=owners)

    assert decision.worker_id == "worker-b"
    assert decision.strategy == "prefix_aware"
    assert "prefix" in decision.reason.lower()


def test_prefix_aware_deterministic_fallback_when_unknown():
    from strategies import PrefixAwareRouter

    router = PrefixAwareRouter()
    workers = _workers()

    d1 = router.choose(workers, prompt="alpha", prefix_owners={})
    d2 = router.choose(workers, prompt="alpha", prefix_owners={})

    assert d1.worker_id == d2.worker_id
    assert d1.strategy == "prefix_aware"
    assert d1.cache_signal == "miss"


def test_shared_prefix_key_ignores_unique_user_suffix():
    from strategies import shared_prefix_key

    system = "You are Atlas."
    a = [
        {"role": "system", "content": system},
        {"role": "user", "content": "ask about cats"},
    ]
    b = [
        {"role": "system", "content": system},
        {"role": "user", "content": "ask about dogs"},
    ]
    assert shared_prefix_key(a) == shared_prefix_key(b)
    assert shared_prefix_key(a) != shared_prefix_key(
        [{"role": "system", "content": "Other system."}, {"role": "user", "content": "x"}]
    )


def test_prefix_aware_miss_claims_via_least_load():
    from strategies import PrefixAwareRouter

    router = PrefixAwareRouter()
    workers = _workers()
    loads = {"worker-a": 4, "worker-b": 0, "worker-c": 2}

    decision = router.choose(
        workers,
        prefix_key="abc123",
        prefix_owners={},
        loads=loads,
    )

    assert decision.worker_id == "worker-b"
    assert decision.cache_signal == "miss"
    assert decision.strategy == "prefix_aware"


def test_choose_raises_when_no_workers():
    from strategies import RoundRobinRouter
    import pytest

    with pytest.raises(ValueError, match="worker"):
        RoundRobinRouter().choose([])


def test_prefix_aware_sticky_when_owner_cool():
    """AC-001: owner load ≤ alternate + margin → hit owner."""
    from strategies import PrefixAwareRouter

    router = PrefixAwareRouter(load_margin=1)
    workers = _workers()
    owners = {"pkey": "worker-a"}
    # 0 < 0+1 → sticky (break only when owner >= alt + margin)
    loads = {"worker-a": 0, "worker-b": 0, "worker-c": 0}

    decision = router.choose(
        workers, prefix_key="pkey", prefix_owners=owners, loads=loads
    )

    assert decision.worker_id == "worker-a"
    assert decision.cache_signal == "hit"
    assert "hit" in decision.reason.lower()


def test_prefix_aware_breaks_when_owner_hot():
    """AC-002: owner load ≥ alternate + margin → cooler worker, hit_broken."""
    from strategies import PrefixAwareRouter

    router = PrefixAwareRouter(load_margin=1)
    workers = _workers()
    owners = {"pkey": "worker-a"}
    loads = {"worker-a": 3, "worker-b": 0, "worker-c": 1}  # 3 >= 0+1 → break

    decision = router.choose(
        workers, prefix_key="pkey", prefix_owners=owners, loads=loads
    )

    assert decision.worker_id == "worker-b"
    assert decision.cache_signal == "hit_broken"
    assert "load_gate" in decision.reason.lower() or "gate" in decision.reason.lower()
    assert decision.strategy == "prefix_aware"


def test_prefix_aware_miss_unchanged_with_gate():
    """AC-003: no owner → least_load miss even when gate configured."""
    from strategies import PrefixAwareRouter

    router = PrefixAwareRouter(load_margin=1)
    workers = _workers()
    loads = {"worker-a": 4, "worker-b": 0, "worker-c": 2}

    decision = router.choose(
        workers, prefix_key="abc123", prefix_owners={}, loads=loads
    )

    assert decision.worker_id == "worker-b"
    assert decision.cache_signal == "miss"


def test_prefix_aware_default_margin_zero_keeps_sticky_under_skew():
    """AC-007: default gate off — hot owner still sticky (Phase 5/7 repro)."""
    from strategies import PrefixAwareRouter

    router = PrefixAwareRouter()  # load_margin default 0
    workers = _workers()
    owners = {"pkey": "worker-a"}
    loads = {"worker-a": 99, "worker-b": 0}

    decision = router.choose(
        workers, prefix_key="pkey", prefix_owners=owners, loads=loads
    )

    assert decision.worker_id == "worker-a"
    assert decision.cache_signal == "hit"
