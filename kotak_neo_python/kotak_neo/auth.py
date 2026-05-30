"""
Kotak Neo Authentication Module
================================
Handles:
  - TOTP generation from a base-32 seed (no manual OTP entry)
  - Username + password login → JWT session token
  - Thread-safe token storage
  - Auto session refresh (keep-alive every N hours via background thread)

Usage:
    auth = KotakNeoAuth(
        consumer_key = os.environ["KOTAK_CONSUMER_KEY"],
        username     = os.environ["KOTAK_USERNAME"],
        password     = os.environ["KOTAK_PASSWORD"],
        totp_seed    = os.environ["KOTAK_TOTP_SEED"],
    )
    auth.login()                  # blocks ~1 s for HTTP round-trip
    auth.start_auto_refresh()     # background keep-alive
    token = auth.get_token()      # get cached JWT
    auth.stop_auto_refresh()
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import pyotp
import requests

from kotak_neo.exceptions import AuthenticationError, SessionExpiredError

logger = logging.getLogger(__name__)


class KotakNeoAuth:
    """
    Manages the Kotak Neo authentication lifecycle.

    All credentials are accepted as constructor arguments.
    Load them from environment variables – never hardcode.
    """

    AUTH_URL = "https://gw-napi.kotaksecurities.com/login/1.0/login/v2/validate"
    DEFAULT_REFRESH_HOURS: float = 4.0     # refresh every 4 h (token valid ~8-12 h)

    def __init__(
        self,
        consumer_key: str,
        username:     str,
        password:     str,
        totp_seed:    str,
        auto_refresh_hours: float = DEFAULT_REFRESH_HOURS,
        session:      Optional[requests.Session] = None,
    ):
        if not all([consumer_key, username, password, totp_seed]):
            raise ValueError("All of consumer_key, username, password, totp_seed are required.")

        self._consumer_key  = consumer_key
        self._username      = username
        self._password      = password
        self._totp_seed     = totp_seed
        self._refresh_hours = auto_refresh_hours

        self._token:   Optional[str] = None
        self._lock     = threading.RLock()
        self._session  = session or requests.Session()

        # Background refresh thread
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def login(self) -> str:
        """
        Perform the full authentication handshake.

        1. Generates the current 6-digit TOTP from the seed.
        2. POSTs credentials to Kotak Neo login endpoint.
        3. Caches and returns the JWT.

        Returns:
            JWT access token string.

        Raises:
            AuthenticationError: if the server rejects credentials.
        """
        with self._lock:
            otp = self._generate_totp()
            logger.info("Initiating Kotak Neo authentication…")

            payload = {
                "userid":   self._username,
                "password": self._password,
                "appCode":  self._consumer_key,
            }
            headers = {
                "Content-Type": "application/json",
                "accept":       "application/json",
                "Neo-API-Key":  self._consumer_key,
                "OTP":          otp,
            }

            try:
                resp = self._session.post(self.AUTH_URL, json=payload, headers=headers, timeout=10)
            except requests.exceptions.RequestException as exc:
                raise AuthenticationError(f"Network error during login: {exc}") from exc

            if resp.status_code == 200:
                data = resp.json()
                token = (data.get("data") or {}).get("token")
                if not token:
                    raise AuthenticationError(
                        f"Login succeeded (HTTP 200) but no token in response. Body: {resp.text}"
                    )
                self._token = token
                logger.info("✅ Kotak Neo authentication successful.")
                return token

            raise AuthenticationError(
                f"Authentication failed.",
                status_code=resp.status_code,
                raw_response=resp.text,
            )

    def get_token(self) -> str:
        """
        Returns the cached JWT.

        Raises:
            SessionExpiredError: if login() has not been called.
        """
        with self._lock:
            if not self._token:
                raise SessionExpiredError("No active session. Call login() first.")
            return self._token

    def invalidate(self) -> None:
        """Clear the cached token (e.g., on 401 from the server)."""
        with self._lock:
            self._token = None
        logger.info("Session token invalidated.")

    def is_authenticated(self) -> bool:
        with self._lock:
            return self._token is not None

    # ------------------------------------------------------------------
    # Auto-refresh (keep-alive)
    # ------------------------------------------------------------------

    def start_auto_refresh(self) -> None:
        """Start background thread that re-authenticates every N hours."""
        if self._refresh_thread and self._refresh_thread.is_alive():
            return  # already running
        self._stop_event.clear()
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            name="kotak-session-refresh",
            daemon=True,
        )
        self._refresh_thread.start()
        logger.info("Session auto-refresh started (every %.1f h).", self._refresh_hours)

    def stop_auto_refresh(self) -> None:
        """Signal the background refresh thread to stop."""
        self._stop_event.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=5)
        logger.info("Session auto-refresh stopped.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_totp(self) -> str:
        """Generate the current 6-digit TOTP from the stored base-32 seed."""
        totp = pyotp.TOTP(self._totp_seed)
        otp  = totp.now()
        logger.debug("TOTP generated.")
        return otp

    def _refresh_loop(self) -> None:
        interval_secs = self._refresh_hours * 3600
        while not self._stop_event.wait(interval_secs):
            logger.info("Scheduled session refresh: re-authenticating…")
            try:
                self.login()
            except AuthenticationError as exc:
                # Log but don't crash – next tick will retry
                logger.error("Session refresh failed (will retry): %s", exc)
