from srag.api.rate_limit import LoginRateLimiter


def _limiter(now):
    box = {"t": now}
    lim = LoginRateLimiter()
    lim._now = lambda: box["t"]
    return lim, box


def test_allows_then_locks_after_five_failures() -> None:
    lim, _box = _limiter(1000.0)
    for _ in range(5):
        assert not lim.is_locked("k")
        lim.record_failure("k")
    assert lim.is_locked("k")


def test_lock_expires() -> None:
    lim, box = _limiter(1000.0)
    for _ in range(5):
        lim.record_failure("k")
    assert lim.is_locked("k")
    box["t"] = 1000.0 + 15 * 60 + 1
    assert not lim.is_locked("k")


def test_success_resets() -> None:
    lim, _box = _limiter(1000.0)
    for _ in range(4):
        lim.record_failure("k")
    lim.record_success("k")
    assert not lim.is_locked("k")
    for _ in range(4):
        lim.record_failure("k")
    assert not lim.is_locked("k")
