"""
Kotak Neo – Custom exception hierarchy.

Catching `KotakNeoError` handles every API-related failure.
More specific sub-types allow fine-grained recovery logic.
"""


class KotakNeoError(Exception):
    """Base exception for all Kotak Neo errors."""

    def __init__(self, message: str, status_code: int | None = None, raw_response: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.raw_response = raw_response

    def __str__(self) -> str:
        base = super().__str__()
        if self.status_code:
            return f"[HTTP {self.status_code}] {base}"
        return base


class AuthenticationError(KotakNeoError):
    """Raised when login or token refresh fails."""


class SessionExpiredError(KotakNeoError):
    """Raised when the server rejects a JWT as expired (HTTP 401/403)."""


class OrderError(KotakNeoError):
    """Raised when an order is rejected, fails validation, or cannot be modified/cancelled."""

    def __init__(self, message: str, order_id: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.order_id = order_id


class RateLimitError(KotakNeoError):
    """Raised when the exchange returns HTTP 429 (Too Many Requests)."""


class MarginError(KotakNeoError):
    """Raised when there is insufficient margin for an order."""


class NetworkError(KotakNeoError):
    """Raised on connection timeouts or network-level failures."""
