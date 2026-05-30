"""
Kotak Neo – Rate Limiter
========================
Enforces Kotak's 10 req/s hard limit.
Uses a token-bucket algorithm so burst allowance is smooth.
"""

from __future__ import annotations

import threading
import time
import logging

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Thread-safe token-bucket rate limiter.

    Args:
        max_calls:   maximum number of calls allowed per `period` seconds.
        period:      time window in seconds (default 1 s).
    """

    def __init__(self, max_calls: int = 9, period: float = 1.0):
        if max_calls < 1:
            raise ValueError("max_calls must be >= 1")
        self._max_calls  = max_calls
        self._period     = period
        self._tokens     = float(max_calls)
        self._lock       = threading.Lock()
        self._last_check = time.monotonic()

    def acquire(self) -> None:
        """
        Block until a call token is available.
        Raises nothing – always eventually returns.
        """
        while True:
            with self._lock:
                now    = time.monotonic()
                elapsed = now - self._last_check
                # Refill tokens proportionally to elapsed time
                self._tokens = min(
                    float(self._max_calls),
                    self._tokens + elapsed * (self._max_calls / self._period),
                )
                self._last_check = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

                # How long until one token is available?
                sleep_for = (1.0 - self._tokens) * (self._period / self._max_calls)

            time.sleep(sleep_for)
