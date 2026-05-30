"""
Kotak Neo – Full API Client
============================
Covers every publicly documented NeoTrade endpoint:

  Authentication
  ─────────────
  • login()               – TOTP-based auto-login
  • logout()              – revoke session

  Orders
  ──────
  • place_order()         – MKT / L / SL / SL-M on any exchange
  • modify_order()        – change qty / price on an open order
  • cancel_order()        – cancel a pending order
  • get_order_book()      – full order history for the session

  Portfolio
  ─────────
  • get_positions()       – intraday & positional open positions
  • get_holdings()        – demat holdings (CNC)
  • get_trade_book()      – executed trades

  Market Data
  ───────────
  • get_quote()           – LTP + OHLCV for one or more symbols
  • get_option_chain()    – full option chain for index/stock

  Margins
  ───────
  • get_margins()         – available / used margin

  GTT Orders
  ──────────
  • place_gtt_order()     – create a Good-Till-Triggered order
  • modify_gtt_order()    – update trigger/limit price
  • cancel_gtt_order()    – delete a GTT order
  • get_gtt_orders()      – list all active GTT orders

  Basket Orders
  ─────────────
  • place_basket_order()  – multi-leg simultaneous placement (₹0 brokerage per leg)

All calls:
  • respect Kotak's 10 req/s limit via TokenBucketRateLimiter
  • retry up to 3 times on transient network failures (5xx)
  • auto-invalidate + raise SessionExpiredError on 401/403
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from kotak_neo.auth import KotakNeoAuth
from kotak_neo.exceptions import (
    KotakNeoError, OrderError, RateLimitError,
    SessionExpiredError, NetworkError,
)
from kotak_neo.models import (
    Order, OrderResponse, OrderBookEntry,
    Position, Holding, Margin, Quote,
    GTTOrder, BasketOrder,
)
from kotak_neo.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)


class KotakNeoClient:
    """
    Thread-safe, production-ready REST client for the Kotak Neo NeoTrade API.

    Usage::

        import os
        from kotak_neo import KotakNeoClient, Order, OrderSide, OrderType, ProductType, Exchange

        client = KotakNeoClient(
            consumer_key = os.environ["KOTAK_CONSUMER_KEY"],
            username     = os.environ["KOTAK_USERNAME"],
            password     = os.environ["KOTAK_PASSWORD"],
            totp_seed    = os.environ["KOTAK_TOTP_SEED"],
        )
        client.login()

        order = Order(
            exchange       = Exchange.NSE,
            trading_symbol = "RELIANCE-EQ",
            side           = OrderSide.BUY,
            order_type     = OrderType.MARKET,
            product        = ProductType.MIS,
            quantity       = 10,
        )
        receipt = client.place_order(order)
        print(receipt.order_id)
    """

    BASE_URL       = "https://gw-napi.kotaksecurities.com/trade/api/v1"
    TIMEOUT        = 10   # seconds per request
    MAX_RETRIES    = 3
    RETRY_BACKOFF  = 0.5  # seconds (doubles each attempt)

    def __init__(
        self,
        consumer_key: str,
        username:     str,
        password:     str,
        totp_seed:    str,
        auto_refresh: bool  = True,
    ):
        self._auth = KotakNeoAuth(
            consumer_key = consumer_key,
            username     = username,
            password     = password,
            totp_seed    = totp_seed,
        )
        self._session      = requests.Session()
        self._rate_limiter = TokenBucketRateLimiter(max_calls=9, period=1.0)
        self._auto_refresh = auto_refresh

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Authenticate and optionally start background token refresh."""
        self._auth.login()
        if self._auto_refresh:
            self._auth.start_auto_refresh()

    def logout(self) -> None:
        """Stop background refresh and clear the session token."""
        self._auth.stop_auto_refresh()
        self._auth.invalidate()
        logger.info("Logged out of Kotak Neo.")

    def is_authenticated(self) -> bool:
        return self._auth.is_authenticated()

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def place_order(self, order: Order) -> OrderResponse:
        """
        Place a single order on the exchange.

        Args:
            order: A validated :class:`Order` instance.

        Returns:
            :class:`OrderResponse` containing the exchange order ID.

        Raises:
            OrderError: if the exchange rejects the order.
        """
        raw = self._post("/orders", order.to_api_dict())
        resp = OrderResponse.from_dict(raw.get("data", raw))
        logger.info("Order placed: id=%s status=%s", resp.order_id, resp.status)
        return resp

    def modify_order(
        self,
        order_id:      str,
        quantity:      int   | None = None,
        price:         float | None = None,
        trigger_price: float | None = None,
        order_type:    str   | None = None,
        validity:      str   | None = None,
    ) -> OrderResponse:
        """Modify an open order's price, quantity, or type."""
        payload: dict[str, Any] = {"nOrdNo": order_id}
        if quantity      is not None: payload["qty"]      = str(quantity)
        if price         is not None: payload["prc"]      = str(price)
        if trigger_price is not None: payload["trgPrc"]   = str(trigger_price)
        if order_type    is not None: payload["prcTp"]    = order_type
        if validity      is not None: payload["vldty"]    = validity
        raw  = self._put("/orders", payload)
        resp = OrderResponse.from_dict(raw.get("data", raw))
        logger.info("Order modified: id=%s", order_id)
        return resp

    def cancel_order(self, order_id: str, is_amo: bool = False) -> OrderResponse:
        """Cancel a pending order."""
        params = {"nOrdNo": order_id, "am": "YES" if is_amo else "NO"}
        raw  = self._delete("/orders", params=params)
        resp = OrderResponse.from_dict(raw.get("data", raw))
        logger.info("Order cancelled: id=%s", order_id)
        return resp

    def get_order_book(self) -> list[OrderBookEntry]:
        """Fetch the full order book for the current session."""
        raw = self._get("/orders")
        return [OrderBookEntry.from_dict(d) for d in (raw.get("data") or [])]

    def get_order_status(self, order_id: str) -> OrderBookEntry:
        """Fetch status for a specific order ID."""
        raw = self._get(f"/order-report/{order_id}")
        data = raw.get("data") or {}
        if isinstance(data, list):
            data = data[0] if data else {}
        return OrderBookEntry.from_dict(data)

    # ------------------------------------------------------------------
    # Portfolio
    # ------------------------------------------------------------------

    def get_positions(self) -> list[Position]:
        """Return all open intraday and positional positions."""
        raw = self._get("/portfolio/positions")
        return [Position.from_dict(d) for d in (raw.get("data") or [])]

    def get_holdings(self) -> list[Holding]:
        """Return demat holdings (CNC delivery positions)."""
        raw = self._get("/portfolio/holdings")
        return [Holding.from_dict(d) for d in (raw.get("data") or [])]

    def get_trade_book(self) -> list[dict]:
        """Return executed trade records for today's session."""
        raw = self._get("/reports/tradeBook")
        return raw.get("data") or []

    # ------------------------------------------------------------------
    # Market Data
    # ------------------------------------------------------------------

    def get_quote(self, instrument_tokens: list[str]) -> list[Quote]:
        """
        Fetch live quotes for one or more instruments.

        Args:
            instrument_tokens: list of strings in the form ``"NSE:RELIANCE-EQ"``
        """
        params = {"instrument_tokens": ",".join(instrument_tokens)}
        raw = self._get("/quotes", params=params)
        return [Quote.from_dict(d) for d in (raw.get("data") or [])]

    def get_option_chain(self, symbol: str, expiry: str, option_type: str = "ALL") -> list[dict]:
        """
        Fetch the option chain for a given symbol and expiry.

        Args:
            symbol:      underlying symbol e.g. ``"NIFTY"``
            expiry:      expiry date e.g. ``"27-Jun-2024"``
            option_type: ``"CE"``, ``"PE"``, or ``"ALL"``
        """
        params = {
            "symbol":      symbol,
            "expiryDate":  expiry,
            "optionType":  option_type,
        }
        raw = self._get("/option-chain", params=params)
        return raw.get("data") or []

    # ------------------------------------------------------------------
    # Margins
    # ------------------------------------------------------------------

    def get_margins(self) -> Margin:
        """Return available and used margin for the account."""
        raw = self._get("/margins")
        return Margin.from_dict(raw.get("data") or {})

    # ------------------------------------------------------------------
    # GTT Orders
    # ------------------------------------------------------------------

    def place_gtt_order(self, gtt: GTTOrder) -> dict:
        """Create a Good-Till-Triggered order."""
        raw = self._post("/gtt/orders", gtt.to_api_dict())
        logger.info("GTT order created: %s", raw)
        return raw.get("data") or raw

    def modify_gtt_order(self, gtt_id: str, trigger_price: float, limit_price: float) -> dict:
        """Update trigger / limit price of an existing GTT order."""
        payload = {
            "id":           gtt_id,
            "triggerPrice": str(trigger_price),
            "price":        str(limit_price),
        }
        raw = self._put("/gtt/orders", payload)
        return raw.get("data") or raw

    def cancel_gtt_order(self, gtt_id: str) -> dict:
        """Delete a GTT order."""
        raw = self._delete("/gtt/orders", params={"id": gtt_id})
        return raw.get("data") or raw

    def get_gtt_orders(self) -> list[dict]:
        """Return all active GTT orders."""
        raw = self._get("/gtt/orders")
        return raw.get("data") or []

    # ------------------------------------------------------------------
    # Basket Orders (multi-leg simultaneous placement)
    # ------------------------------------------------------------------

    def place_basket_order(self, basket: BasketOrder) -> list[OrderResponse]:
        """
        Place all orders in the basket simultaneously.
        Each leg carries ₹0 brokerage on the Trade API plan.
        """
        raw = self._post("/basket-order", basket.to_api_dict())
        results = raw.get("data") or []
        responses = [OrderResponse.from_dict(r) for r in results]
        logger.info("Basket '%s' submitted: %d legs", basket.name, len(responses))
        return responses

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type":  "application/json",
            "accept":        "application/json",
            "Neo-API-Key":   self._auth._consumer_key,
            "Authorization": f"Bearer {self._auth.get_token()}",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params=params)

    def _post(self, path: str, payload: dict) -> dict:
        return self._request("POST", path, json=payload)

    def _put(self, path: str, payload: dict) -> dict:
        return self._request("PUT", path, json=payload)

    def _delete(self, path: str, params: dict | None = None) -> dict:
        return self._request("DELETE", path, params=params)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = self.BASE_URL + path
        last_exc: Exception | None = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            self._rate_limiter.acquire()
            try:
                resp = self._session.request(
                    method,
                    url,
                    headers=self._headers(),
                    timeout=self.TIMEOUT,
                    **kwargs,
                )
            except requests.exceptions.RequestException as exc:
                last_exc = NetworkError(f"Network error on {method} {path}: {exc}")
                logger.warning("Request attempt %d/%d failed: %s", attempt, self.MAX_RETRIES, exc)
                time.sleep(self.RETRY_BACKOFF * (2 ** (attempt - 1)))
                continue

            if resp.status_code in (200, 201):
                return resp.json()

            if resp.status_code == 401 or resp.status_code == 403:
                self._auth.invalidate()
                raise SessionExpiredError(
                    "Token rejected (HTTP %d). Call login() to re-authenticate." % resp.status_code,
                    status_code=resp.status_code,
                    raw_response=resp.text,
                )

            if resp.status_code == 429:
                raise RateLimitError(
                    "Rate limit hit (HTTP 429). Reduce call frequency.",
                    status_code=429,
                    raw_response=resp.text,
                )

            if 500 <= resp.status_code < 600:
                logger.warning(
                    "Server error HTTP %d on attempt %d/%d. Retrying…",
                    resp.status_code, attempt, self.MAX_RETRIES,
                )
                last_exc = KotakNeoError(
                    f"Server error on {method} {path}",
                    status_code=resp.status_code,
                    raw_response=resp.text,
                )
                time.sleep(self.RETRY_BACKOFF * (2 ** (attempt - 1)))
                continue

            # 4xx – client error, don't retry
            raise OrderError(
                f"Request failed: {resp.text}",
                status_code=resp.status_code,
                raw_response=resp.text,
            )

        raise last_exc or KotakNeoError(f"All {self.MAX_RETRIES} attempts failed for {method} {path}")
