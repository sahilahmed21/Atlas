"""Demo load mixer: multi-prefix, not a single-hash metronome."""

from __future__ import annotations

import random

from demo_load import _build_bodies, _prefix_diversity, realistic


def test_realistic_has_many_system_prefixes():
    random.seed(7)
    bodies = realistic(40, tenants=5)
    assert _prefix_diversity(bodies) >= 4


def test_realistic_avoids_long_same_prefix_runs():
    random.seed(11)
    bodies = realistic(48, tenants=5)
    systems = []
    for b in bodies:
        for m in b["messages"]:
            if m["role"] == "system":
                systems.append(m["content"])
                break
    longest = 1
    run = 1
    for i in range(1, len(systems)):
        if systems[i] == systems[i - 1]:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    # Cap in mixer is 3 consecutive; allow a little slack for edge picks.
    assert longest <= 3


def test_default_mix_is_realistic_and_diverse():
    random.seed(3)
    bodies = _build_bodies(36, "realistic", tenants=5)
    assert _prefix_diversity(bodies) >= 4


def test_sticky_is_single_prefix_by_design():
    bodies = _build_bodies(24, "sticky", tenants=5)
    assert _prefix_diversity(bodies) == 1
