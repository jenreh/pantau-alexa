"""In-memory sliding-window rate limiter for auth-sensitive HTTP endpoints.

Single-process only (matches the single-uvicorn-worker deployment). For a
multi-worker setup this would need a shared backend (e.g. Redis).
"""

from __future__ import annotations

import logging
import time
from collections import deque

log = logging.getLogger(__name__)

_CLEANUP_THRESHOLD = 10_000  # keys; prevents unbounded growth under key churn


class SlidingWindowRateLimiter:
    """Allows at most *max_attempts* events per *window_seconds* per key."""

    def __init__(self, max_attempts: int, window_seconds: float) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        """Record an attempt for *key*; returns False once the limit is hit."""
        now = time.monotonic()
        cutoff = now - self._window_seconds

        attempts = self._attempts.setdefault(key, deque())
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

        if len(attempts) >= self._max_attempts:
            log.warning("Rate limit exceeded for key: %s", key)
            return False

        attempts.append(now)
        if len(self._attempts) > _CLEANUP_THRESHOLD:
            self._drop_expired(cutoff)
        return True

    def _drop_expired(self, cutoff: float) -> None:
        expired = [
            key
            for key, attempts in self._attempts.items()
            if not attempts or attempts[-1] <= cutoff
        ]
        for key in expired:
            del self._attempts[key]
