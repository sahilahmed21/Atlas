"""RED/GREEN Phase 12: seeded fault schedule is a pure function of (seed, step, rate)."""

from recording import FAULT_KINDS, fault_for


def _schedule(seed, rate=0.5, steps=200):
    return [fault_for(seed, s, rate) for s in range(steps)]


def test_same_seed_gives_the_identical_schedule_every_time():
    first = _schedule(42)
    assert all(_schedule(42) == first for _ in range(100))


def test_different_seeds_diverge():
    assert _schedule(1) != _schedule(2)


def test_rate_bounds_and_kinds():
    assert set(_schedule(7, rate=0.0)) == {None}
    everything = _schedule(7, rate=1.0)
    assert None not in everything and set(everything) <= set(FAULT_KINDS)
    assert len(set(everything)) == len(FAULT_KINDS)  # every kind is reachable


def test_observed_fault_fraction_tracks_the_rate():
    hit = sum(1 for f in _schedule(3, rate=0.25, steps=4000) if f)
    assert 0.20 < hit / 4000 < 0.30


def test_a_step_does_not_depend_on_other_steps():
    assert fault_for(9, 5, 0.5) == _schedule(9)[5]
