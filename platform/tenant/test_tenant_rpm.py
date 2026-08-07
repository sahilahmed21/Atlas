"""RED/GREEN: process-local RPM limiter (AC-008)."""


def test_process_local_rpm_allows_under_limit():
    from rpm import ProcessLocalRPMLimiter

    lim = ProcessLocalRPMLimiter(clock=lambda: 1000.0)
    assert lim.try_acquire("demo", limit=2) is True
    assert lim.try_acquire("demo", limit=2) is True
    assert lim.try_acquire("demo", limit=2) is False


def test_process_local_rpm_window_expires():
    from rpm import ProcessLocalRPMLimiter

    t = {"now": 0.0}

    def clock():
        return t["now"]

    lim = ProcessLocalRPMLimiter(window_s=60.0, clock=clock)
    assert lim.try_acquire("demo", limit=2) is True
    assert lim.try_acquire("demo", limit=2) is True
    assert lim.try_acquire("demo", limit=2) is False
    t["now"] = 61.0
    assert lim.try_acquire("demo", limit=2) is True


def test_rpm_scope_constant_is_honest():
    from rpm import RPM_SCOPE

    assert RPM_SCOPE == "process-local"
    assert "production" not in RPM_SCOPE.lower()
