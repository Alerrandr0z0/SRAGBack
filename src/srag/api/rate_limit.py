"""In-memory login rate limiter.

Mirrors the reference ``LoginRateLimiter``: at most 5 failed attempts per
key inside a 15-minute window, then a 15-minute lock.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60
LOCK_SECONDS = 15 * 60


@dataclass
class _AttemptState:
    first_attempt_at: float
    failed_attempts: int = 0
    locked_until: float | None = None


@dataclass
class LoginRateLimiter:
    """Track failed logins per key with lockout (injectable clock for tests)."""

    _states: dict[str, _AttemptState] = field(default_factory=dict)
    _now: callable = time.monotonic  # type: ignore[assignment]

    def is_locked(self, key: str) -> bool:
        """Return True when ``key`` is currently locked out."""
        state = self._states.get(key)
        if state is None:
            return False
        now = self._now()
        if state.locked_until is not None and state.locked_until > now:
            return True
        if state.first_attempt_at + WINDOW_SECONDS <= now:
            self._states.pop(key, None)
        return False

    def record_failure(self, key: str) -> None:
        """Record a failed attempt; lock ``key`` after MAX_ATTEMPTS in-window."""
        now = self._now()
        state = self._states.get(key)
        if state is None or state.first_attempt_at + WINDOW_SECONDS <= now:
            state = _AttemptState(first_attempt_at=now)
            self._states[key] = state
        state.failed_attempts += 1
        if state.failed_attempts >= MAX_ATTEMPTS:
            state.locked_until = now + LOCK_SECONDS

    def record_success(self, key: str) -> None:
        """Clear any failure state for ``key``."""
        self._states.pop(key, None)


limiter = LoginRateLimiter()
