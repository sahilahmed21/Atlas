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
    assert "fallback" in d1.reason.lower()


def test_choose_raises_when_no_workers():
    from strategies import RoundRobinRouter
    import pytest

    with pytest.raises(ValueError, match="worker"):
        RoundRobinRouter().choose([])
