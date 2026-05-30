"""
KotakNeoBroker – AbstractBroker implementation for Kotak Neo NeoTrade API.

Plugs directly into the existing broker factory:
    from brokers.kotak_neo_broker import KotakNeoBroker
    BrokerFactory.AVAILABLE_BROKERS['kotak_neo'] = KotakNeoBroker

Authentication credentials are loaded from .env:
    KOTAK_CONSUMER_KEY
    KOTAK_USERNAME
    KOTAK_PASSWORD
    KOTAK_TOTP_SEED
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Allow importing from the sibling kotak_neo_python package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kotak_neo_python"))

from kotak_neo.client import KotakNeoClient
from kotak_neo.models import (
    Order as NeoOrder,
    OrderSide, OrderType as NeoOrderType, ProductType as NeoProductType,
    Exchange as NeoExchange, Validity as NeoValidity,
)
from kotak_neo.exceptions import KotakNeoError, SessionExpiredError

from brokers.abstract_broker import (
    AbstractBroker, BrokerOrder, BrokerOrderResponse,
    BrokerPosition, BrokerBalance, BrokerError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Field mapping helpers
# ---------------------------------------------------------------------------

_SIDE_MAP: dict[str, OrderSide] = {
    "BUY":  OrderSide.BUY,
    "SELL": OrderSide.SELL,
    "B":    OrderSide.BUY,
    "S":    OrderSide.SELL,
}

_ORDER_TYPE_MAP: dict[str, NeoOrderType] = {
    "MARKET": NeoOrderType.MARKET,
    "MKT":    NeoOrderType.MARKET,
    "LIMIT":  NeoOrderType.LIMIT,
    "L":      NeoOrderType.LIMIT,
    "SL-M":   NeoOrderType.STOP_LOSS_M,
    "SL":     NeoOrderType.STOP_LOSS,
    "SL-L":   NeoOrderType.STOP_LOSS,
}

_PRODUCT_MAP: dict[str, NeoProductType] = {
    "MIS":  NeoProductType.MIS,
    "CNC":  NeoProductType.CNC,
    "NRML": NeoProductType.NRML,
}


class KotakNeoBroker(AbstractBroker):
    """
    Kotak Neo NeoTrade API broker.

    Credentials are read from environment variables:
        KOTAK_CONSUMER_KEY  – your Neo developer consumer key
        KOTAK_USERNAME      – your Kotak Neo user ID
        KOTAK_PASSWORD      – your Kotak Neo password
        KOTAK_TOTP_SEED     – base-32 TOTP seed from authenticator app

    Features vs other brokers:
        ✅ ₹0 brokerage on Trade API (all plans)
        ✅ TOTP-based automated daily login
        ✅ Auto session keep-alive (refreshes every 4 h)
        ✅ GTT orders
        ✅ Basket orders
        ✅ WebSocket live tick streaming
        ✅ NSE + BSE + NFO + BFO + CDS + MCX
    """

    def __init__(self):
        super().__init__("kotak_neo")
        self._client: Optional[KotakNeoClient] = None

    # ------------------------------------------------------------------
    # AbstractBroker: authenticate
    # ------------------------------------------------------------------

    def authenticate(self, credentials: Dict[str, str]) -> Tuple[bool, str]:
        """
        Authenticate with Kotak Neo.

        Credentials dict keys (all required):
            consumer_key, username, password, totp_seed

        Or pass an empty dict to read from environment variables.
        """
        consumer_key = credentials.get("consumer_key") or os.getenv("KOTAK_CONSUMER_KEY", "")
        username     = credentials.get("username")     or os.getenv("KOTAK_USERNAME", "")
        password     = credentials.get("password")     or os.getenv("KOTAK_PASSWORD", "")
        totp_seed    = credentials.get("totp_seed")    or os.getenv("KOTAK_TOTP_SEED", "")

        if not all([consumer_key, username, password, totp_seed]):
            return False, (
                "Missing credentials. Set KOTAK_CONSUMER_KEY, KOTAK_USERNAME, "
                "KOTAK_PASSWORD, KOTAK_TOTP_SEED in your .env file."
            )

        try:
            self._client = KotakNeoClient(
                consumer_key = consumer_key,
                username     = username,
                password     = password,
                totp_seed    = totp_seed,
                auto_refresh = True,
            )
            self._client.login()
            self.is_connected = True
            logger.info("✅ Connected to Kotak Neo (₹0 brokerage Trade API)")
            return True, f"Connected to Kotak Neo as {username}"

        except KotakNeoError as exc:
            logger.error("Kotak Neo auth failed: %s", exc)
            return False, str(exc)

    # ------------------------------------------------------------------
    # AbstractBroker: quotes
    # ------------------------------------------------------------------

    def get_quote(self, symbol: str) -> Dict[str, float]:
        self._require_connected()
        try:
            token = f"NSE:{symbol}"
            quotes = self._client.get_quote([token])
            if not quotes:
                return {}
            q = quotes[0]
            return {
                "ltp":        q.ltp,
                "open":       q.open,
                "high":       q.high,
                "low":        q.low,
                "close":      q.close,
                "volume":     q.volume,
                "bid":        q.bid,
                "ask":        q.ask,
                "change":     q.change,
                "change_pct": q.change_pct,
            }
        except KotakNeoError as exc:
            raise BrokerError(str(exc)) from exc

    def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        self._require_connected()
        tokens = [f"NSE:{s}" for s in symbols]
        try:
            quotes = self._client.get_quote(tokens)
            return {
                q.trading_symbol.replace("-EQ", ""): {
                    "ltp": q.ltp, "open": q.open, "high": q.high,
                    "low": q.low, "close": q.close, "volume": q.volume,
                }
                for q in quotes
            }
        except KotakNeoError as exc:
            raise BrokerError(str(exc)) from exc

    # ------------------------------------------------------------------
    # AbstractBroker: place / cancel / get orders
    # ------------------------------------------------------------------

    def place_order(self, order: BrokerOrder) -> Tuple[bool, str, Optional[str]]:
        self._require_connected()
        try:
            neo_order = NeoOrder(
                exchange        = NeoExchange.NSE,
                trading_symbol  = order.symbol,
                side            = _SIDE_MAP.get(order.side.upper(), OrderSide.BUY),
                order_type      = _ORDER_TYPE_MAP.get(order.order_type.upper(), NeoOrderType.MARKET),
                product         = _PRODUCT_MAP.get(order.product.upper(), NeoProductType.MIS),
                quantity        = order.quantity,
                price           = order.price or 0.0,
                trigger_price   = order.trigger_price or 0.0,
                validity        = NeoValidity.DAY,
            )
            resp = self._client.place_order(neo_order)
            return True, f"Order placed: {resp.status}", resp.order_id

        except SessionExpiredError:
            logger.warning("Session expired – re-logging in…")
            self._client.login()
            return self.place_order(order)   # single retry after re-login
        except KotakNeoError as exc:
            logger.error("Order failed: %s", exc)
            return False, str(exc), None

    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        self._require_connected()
        try:
            resp = self._client.cancel_order(order_id)
            return True, f"Cancelled: {resp.status}"
        except KotakNeoError as exc:
            return False, str(exc)

    def get_orders(self, status: Optional[str] = None) -> List[BrokerOrder]:
        self._require_connected()
        try:
            entries = self._client.get_order_book()
            result  = []
            for e in entries:
                if status and e.status.value.lower() != status.lower():
                    continue
                result.append(BrokerOrder(
                    symbol     = e.trading_symbol,
                    side       = e.side,
                    quantity   = e.quantity,
                    price      = e.price,
                    order_type = e.order_type,
                    product    = e.product,
                    order_id   = e.order_id,
                ))
            return result
        except KotakNeoError as exc:
            raise BrokerError(str(exc)) from exc

    # ------------------------------------------------------------------
    # AbstractBroker: positions / balance
    # ------------------------------------------------------------------

    def get_positions(self) -> List[BrokerPosition]:
        self._require_connected()
        try:
            positions = self._client.get_positions()
            return [
                BrokerPosition(
                    symbol        = p.trading_symbol,
                    quantity      = abs(p.quantity),
                    avg_price     = p.avg_price,
                    current_price = p.ltp,
                    pnl           = p.pnl,
                    pnl_pct       = (p.pnl / (abs(p.quantity) * p.avg_price) * 100)
                                    if p.quantity and p.avg_price else 0.0,
                    side          = p.side,
                    exchange      = p.exchange,
                )
                for p in positions
            ]
        except KotakNeoError as exc:
            raise BrokerError(str(exc)) from exc

    def get_balance(self) -> BrokerBalance:
        self._require_connected()
        try:
            margin = self._client.get_margins()
            return BrokerBalance(
                available_cash   = margin.available_cash,
                used_margin      = margin.used_margin,
                available_margin = margin.available_margin,
                total_equity     = margin.total_equity,
                product_balance  = {},
            )
        except KotakNeoError as exc:
            raise BrokerError(str(exc)) from exc

    def get_historical_data(self, symbol: str, interval: str,
                            start_date: str, end_date: str) -> Dict:
        """
        Note: Kotak Neo REST API does not currently expose a historical data
        endpoint in their public Trade API. Use an alternative data source
        (Yahoo Finance, NSE direct, etc.) for backtesting.
        """
        raise NotImplementedError(
            "Kotak Neo Trade API does not provide historical OHLCV data. "
            "Use historical_data_engine.py with an alternative provider."
        )

    # ------------------------------------------------------------------
    # Kotak Neo-specific extras (not in AbstractBroker)
    # ------------------------------------------------------------------

    def get_holdings(self):
        """Demat holdings (CNC delivery positions)."""
        self._require_connected()
        return self._client.get_holdings()

    def place_gtt_order(self, gtt):
        """Place a Good-Till-Triggered order."""
        self._require_connected()
        return self._client.place_gtt_order(gtt)

    def place_basket_order(self, basket):
        """Multi-leg basket order (₹0 brokerage per leg on Trade API)."""
        self._require_connected()
        return self._client.place_basket_order(basket)

    def get_option_chain(self, symbol: str, expiry: str, option_type: str = "ALL"):
        """Fetch full option chain for index or stock."""
        self._require_connected()
        return self._client.get_option_chain(symbol, expiry, option_type)

    def get_websocket(self):
        """Return a configured, ready-to-connect WebSocket client."""
        from kotak_neo.websocket_client import KotakNeoWebSocket
        return KotakNeoWebSocket(self._client)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _require_connected(self) -> None:
        if not self.is_connected or not self._client:
            raise BrokerError("Not connected to Kotak Neo. Call authenticate() first.")
