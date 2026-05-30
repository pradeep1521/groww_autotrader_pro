"""
Kotak Neo Python Client
=======================
Production-grade Python client for the Kotak Neo NeoTrade API.

Features covered:
  - Zero-brokerage Trade API (₹0 on all 3 plans)
  - TOTP-based automated daily login (no manual OTP entry)
  - Orders: Place / Modify / Cancel (MKT, L, SL, SL-M)
  - Product types: MIS (intraday), CNC (delivery), NRML (carry-forward)
  - Exchanges: NSE, BSE, NFO, BFO, CDS, MCX
  - GTT (Good Till Triggered) orders
  - Basket orders (multi-leg simultaneous placement)
  - Portfolio: Positions, Holdings, Order Book, Trade Book
  - Margins: Used / Available
  - WebSocket: Real-time tick streaming + order-update feed
  - Rate limiter (stays under Kotak's 10 req/s hard limit)
  - Auto session refresh (keep-alive every 4 hours)
"""

from kotak_neo.client import KotakNeoClient
from kotak_neo.auth import KotakNeoAuth
from kotak_neo.models import (
    Order, OrderSide, OrderType, ProductType, Exchange, Validity,
    GTTOrder, BasketOrder, Position, Holding, OrderStatus,
)
from kotak_neo.exceptions import (
    KotakNeoError, AuthenticationError, OrderError,
    RateLimitError, SessionExpiredError,
)
from kotak_neo.websocket_client import KotakNeoWebSocket

__version__ = "1.0.0"
__all__ = [
    "KotakNeoClient",
    "KotakNeoAuth",
    "Order",
    "OrderSide",
    "OrderType",
    "ProductType",
    "Exchange",
    "Validity",
    "GTTOrder",
    "BasketOrder",
    "Position",
    "Holding",
    "OrderStatus",
    "KotakNeoError",
    "AuthenticationError",
    "OrderError",
    "RateLimitError",
    "SessionExpiredError",
    "KotakNeoWebSocket",
]
