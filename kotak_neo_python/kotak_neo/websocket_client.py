"""
Kotak Neo – WebSocket Streaming Client
========================================
Subscribes to Kotak Neo's live market-data feed over a persistent WebSocket.

Features:
  - Real-time tick streaming (LTP, OHLCV, depth)
  - Order-update feed (execution confirmations)
  - Automatic reconnect with exponential back-off
  - Per-symbol callback registration
  - Thread-safe subscribe / unsubscribe at runtime

Usage::

    from kotak_neo import KotakNeoClient, KotakNeoWebSocket

    client = KotakNeoClient(...)
    client.login()

    def on_tick(tick: dict) -> None:
        print(tick["symbol"], tick["ltp"])

    ws = KotakNeoWebSocket(client)
    ws.on_tick   = on_tick
    ws.on_order  = lambda msg: print("Order update:", msg)
    ws.on_error  = lambda e:   print("WS error:", e)

    ws.subscribe(["nse_cm|2885", "nse_cm|5926"])  # instrument tokens
    ws.connect()          # non-blocking; runs in background thread

    # ... do other work ...

    ws.unsubscribe(["nse_cm|2885"])
    ws.disconnect()

Instrument Token Format
-----------------------
Kotak uses ``"<exchange_segment>|<instrument_token>"`` pairs, e.g.:

  - NSE equities : ``"nse_cm|2885"``      (RELIANCE)
  - NFO options  : ``"nse_fo|35001"``
  - BSE equities : ``"bse_cm|500325"``
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Callable, Optional

import websocket  # websocket-client

from kotak_neo.auth import KotakNeoAuth

logger = logging.getLogger(__name__)

# Kotak Neo WebSocket feed URL
_WS_URL = "wss://mlhsm.kotaksecurities.com"

# Subscription message types
_SUBSCRIBE_TYPE   = "mws"    # market-data subscription
_UNSUBSCRIBE_TYPE = "mwu"    # market-data unsubscription
_ORDER_SUB_TYPE   = "ord"    # order-update subscription


class KotakNeoWebSocket:
    """
    Persistent WebSocket client for Kotak Neo live data feed.

    All callbacks run on a background thread spawned by the websocket-client
    library. Keep them non-blocking; offload heavy work to a queue.
    """

    MAX_RECONNECT_DELAY = 60   # seconds
    INITIAL_DELAY       = 1    # seconds

    def __init__(self, client_or_auth, ws_url: str = _WS_URL):
        """
        Args:
            client_or_auth: either a :class:`KotakNeoClient` or a
                            :class:`KotakNeoAuth` instance – used to get
                            the current JWT and consumer key.
            ws_url:         override the default WebSocket endpoint.
        """
        # Accept both the full client and just the auth object
        if hasattr(client_or_auth, "_auth"):
            self._auth: KotakNeoAuth = client_or_auth._auth
            self._consumer_key: str  = client_or_auth._auth._consumer_key
        else:
            self._auth          = client_or_auth
            self._consumer_key  = client_or_auth._consumer_key

        self._ws_url     = ws_url
        self._ws:        Optional[websocket.WebSocketApp] = None
        self._thread:    Optional[threading.Thread]       = None
        self._stop_flag  = threading.Event()

        # Subscriptions
        self._subscribed_tokens: set[str] = set()
        self._sub_lock = threading.Lock()

        # Reconnect state
        self._reconnect_delay = self.INITIAL_DELAY

        # Public callbacks – override these
        self.on_tick:  Callable[[dict], None] = lambda tick: None
        self.on_order: Callable[[dict], None] = lambda msg:  None
        self.on_error: Callable[[Exception], None] = lambda e: None
        self.on_open:  Callable[[], None]     = lambda: None
        self.on_close: Callable[[], None]     = lambda: None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(self, tokens: list[str]) -> None:
        """
        Subscribe to live ticks for the given instrument tokens.
        Can be called before or after :meth:`connect`.

        Args:
            tokens: e.g. ``["nse_cm|2885", "nse_fo|35001"]``
        """
        with self._sub_lock:
            self._subscribed_tokens.update(tokens)
        if self._ws and self._ws.sock and self._ws.sock.connected:
            self._send_subscribe(tokens)

    def unsubscribe(self, tokens: list[str]) -> None:
        """Unsubscribe from live ticks for the given tokens."""
        with self._sub_lock:
            self._subscribed_tokens.difference_update(tokens)
        if self._ws and self._ws.sock and self._ws.sock.connected:
            self._send_unsubscribe(tokens)

    def connect(self, block: bool = False) -> None:
        """
        Open the WebSocket connection.

        Args:
            block: if True, block the calling thread until disconnected.
                   Default False (runs in background thread).
        """
        self._stop_flag.clear()
        self._start_ws_thread(block=block)

    def disconnect(self) -> None:
        """Close the connection and stop the background thread."""
        self._stop_flag.set()
        if self._ws:
            self._ws.close()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("WebSocket disconnected.")

    # ------------------------------------------------------------------
    # WebSocket callbacks (internal)
    # ------------------------------------------------------------------

    def _on_open(self, ws) -> None:
        logger.info("WebSocket connected to %s", self._ws_url)
        self._reconnect_delay = self.INITIAL_DELAY  # reset back-off

        # Authenticate the WebSocket session
        auth_msg = json.dumps({
            "type":       "login",
            "Authorization": f"Bearer {self._auth.get_token()}",
            "Sid":        self._auth._consumer_key,
        })
        ws.send(auth_msg)

        # Subscribe to order updates
        ws.send(json.dumps({"type": _ORDER_SUB_TYPE}))

        # Re-subscribe to any previously registered market tokens
        with self._sub_lock:
            tokens = list(self._subscribed_tokens)
        if tokens:
            self._send_subscribe(tokens)

        self.on_open()

    def _on_message(self, ws, raw_message: str) -> None:
        try:
            msg = json.loads(raw_message)
        except json.JSONDecodeError:
            logger.debug("Non-JSON WebSocket frame: %s", raw_message[:120])
            return

        msg_type = msg.get("type", "")

        if msg_type in ("mws", "tick", "market"):
            self.on_tick(self._parse_tick(msg))
        elif msg_type in ("ord", "order"):
            self.on_order(msg)
        else:
            logger.debug("WS message type='%s': %s", msg_type, str(msg)[:200])

    def _on_error(self, ws, error) -> None:
        logger.error("WebSocket error: %s", error)
        self.on_error(error)

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        logger.warning("WebSocket closed (code=%s msg=%s)", close_status_code, close_msg)
        self.on_close()

        if not self._stop_flag.is_set():
            logger.info("Reconnecting in %d s…", self._reconnect_delay)
            time.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, self.MAX_RECONNECT_DELAY)
            self._start_ws_thread()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _start_ws_thread(self, block: bool = False) -> None:
        url = (
            f"{self._ws_url}"
            f"?Authorization={self._auth.get_token()}"
            f"&Sid={self._consumer_key}"
        )
        self._ws = websocket.WebSocketApp(
            url,
            on_open    = self._on_open,
            on_message = self._on_message,
            on_error   = self._on_error,
            on_close   = self._on_close,
        )
        if block:
            self._ws.run_forever(ping_interval=30, ping_timeout=10)
        else:
            self._thread = threading.Thread(
                target=self._ws.run_forever,
                kwargs={"ping_interval": 30, "ping_timeout": 10},
                name="kotak-websocket",
                daemon=True,
            )
            self._thread.start()

    def _send_subscribe(self, tokens: list[str]) -> None:
        msg = json.dumps({
            "type":   _SUBSCRIBE_TYPE,
            "tokens": tokens,
        })
        if self._ws:
            self._ws.send(msg)
        logger.debug("Subscribed to: %s", tokens)

    def _send_unsubscribe(self, tokens: list[str]) -> None:
        msg = json.dumps({
            "type":   _UNSUBSCRIBE_TYPE,
            "tokens": tokens,
        })
        if self._ws:
            self._ws.send(msg)
        logger.debug("Unsubscribed from: %s", tokens)

    @staticmethod
    def _parse_tick(msg: dict) -> dict:
        """Normalize a raw WebSocket tick frame to a consistent dict."""
        return {
            "symbol":       msg.get("trdSym", msg.get("symbol", "")),
            "exchange":     msg.get("exSeg",  msg.get("exchange", "")),
            "ltp":          float(msg.get("ltp",    0) or 0),
            "open":         float(msg.get("open",   0) or 0),
            "high":         float(msg.get("high",   0) or 0),
            "low":          float(msg.get("low",    0) or 0),
            "close":        float(msg.get("close",  0) or 0),
            "volume":       int(msg.get("vol",      0) or 0),
            "bid":          float(msg.get("bid",    0) or 0),
            "ask":          float(msg.get("ask",    0) or 0),
            "timestamp":    msg.get("ltt",  msg.get("ts", "")),
            "raw":          msg,
        }
