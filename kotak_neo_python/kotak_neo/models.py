"""
Data models for the Kotak Neo API.

Uses Python dataclasses (stdlib only – no external dependency).
All field names mirror the Kotak Neo API response keys so that
`Model.from_dict(response_json["data"])` works without mapping layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class OrderSide(str, Enum):
    BUY  = "B"
    SELL = "S"


class OrderType(str, Enum):
    MARKET       = "MKT"
    LIMIT        = "L"
    STOP_LOSS    = "SL"       # Limit SL
    STOP_LOSS_M  = "SL-M"    # Market SL


class ProductType(str, Enum):
    MIS  = "MIS"   # Intraday margin
    CNC  = "CNC"   # Delivery
    NRML = "NRML"  # Carry-forward (F&O)


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"   # NSE F&O
    BFO = "BFO"   # BSE F&O
    CDS = "CDS"   # Currency derivatives
    MCX = "MCX"   # Commodity


class Validity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"   # Immediate or cancel
    GTC = "GTC"   # Good till cancelled (for GTT)


class OrderStatus(str, Enum):
    OPEN             = "open"
    COMPLETE         = "complete"
    CANCELLED        = "cancelled"
    REJECTED         = "rejected"
    PARTIALLY_FILLED = "partially_filled"
    PENDING          = "pending"
    UNKNOWN          = "unknown"

    @classmethod
    def from_api(cls, raw: str | None) -> "OrderStatus":
        if not raw:
            return cls.UNKNOWN
        mapping = {
            "complete":      cls.COMPLETE,
            "filled":        cls.COMPLETE,
            "open":          cls.OPEN,
            "opn":           cls.OPEN,
            "cancelled":     cls.CANCELLED,
            "cancel":        cls.CANCELLED,
            "rejected":      cls.REJECTED,
            "rej":           cls.REJECTED,
            "partial fill":  cls.PARTIALLY_FILLED,
            "partial_fill":  cls.PARTIALLY_FILLED,
            "pending":       cls.PENDING,
            "put order req received": cls.PENDING,
        }
        return mapping.get(raw.strip().lower(), cls.UNKNOWN)


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

@dataclass
class Order:
    """Input model for placing a new order."""
    exchange:      Exchange
    trading_symbol: str
    side:          OrderSide
    order_type:    OrderType
    product:       ProductType
    quantity:      int
    price:         float        = 0.0   # 0 for MARKET
    trigger_price: float        = 0.0   # for SL / SL-M
    validity:      Validity     = Validity.DAY
    disclosed_qty: int          = 0
    tag:           str          = ""    # client-side correlation tag (max 20 chars)
    amo:           bool         = False  # After Market Order

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("quantity must be > 0")
        if self.order_type == OrderType.LIMIT and self.price <= 0:
            raise ValueError("price must be > 0 for LIMIT orders")
        if self.order_type in (OrderType.STOP_LOSS, OrderType.STOP_LOSS_M) and self.trigger_price <= 0:
            raise ValueError("trigger_price must be > 0 for SL/SL-M orders")
        if self.tag and len(self.tag) > 20:
            raise ValueError("tag must be ≤ 20 characters")

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize to the Kotak Neo REST API payload format."""
        payload: dict[str, Any] = {
            "exchange":        self.exchange.value,
            "tradingSymbol":   self.trading_symbol,
            "transactionType": self.side.value,
            "orderType":       self.order_type.value,
            "product":         self.product.value,
            "quantity":        str(self.quantity),
            "price":           str(self.price),
            "triggerPrice":    str(self.trigger_price),
            "validity":        self.validity.value,
            "disclosedQty":    str(self.disclosed_qty),
            "amo":             "YES" if self.amo else "NO",
        }
        if self.tag:
            payload["tag"] = self.tag
        return payload


# ---------------------------------------------------------------------------
# Order Response
# ---------------------------------------------------------------------------

@dataclass
class OrderResponse:
    """Response returned after place/modify/cancel operations."""
    order_id:   str
    status:     OrderStatus
    message:    str          = ""
    raw:        dict         = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "OrderResponse":
        return cls(
            order_id = data.get("nOrdNo", data.get("ordId", "")),
            status   = OrderStatus.from_api(data.get("ordSt")),
            message  = data.get("rejRsn", data.get("message", "")),
            raw      = data,
        )


# ---------------------------------------------------------------------------
# Order Book Entry
# ---------------------------------------------------------------------------

@dataclass
class OrderBookEntry:
    order_id:      str
    trading_symbol: str
    exchange:      str
    side:          str
    order_type:    str
    product:       str
    quantity:      int
    filled_qty:    int
    price:         float
    avg_price:     float
    status:        OrderStatus
    reject_reason: str
    timestamp:     datetime | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "OrderBookEntry":
        ts = None
        raw_ts = d.get("ordDttm") or d.get("ordTm")
        if raw_ts:
            try:
                ts = datetime.strptime(raw_ts, "%d-%b-%Y %H:%M:%S")
            except ValueError:
                pass
        return cls(
            order_id       = d.get("nOrdNo", ""),
            trading_symbol = d.get("trdSym", ""),
            exchange       = d.get("exSeg", ""),
            side           = d.get("trnsTp", ""),
            order_type     = d.get("prcTp", ""),
            product        = d.get("prod", ""),
            quantity       = int(d.get("qty", 0) or 0),
            filled_qty     = int(d.get("fldQty", 0) or 0),
            price          = float(d.get("prc", 0) or 0),
            avg_price      = float(d.get("avgPrc", 0) or 0),
            status         = OrderStatus.from_api(d.get("ordSt")),
            reject_reason  = d.get("rejRsn", ""),
            timestamp      = ts,
        )


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

@dataclass
class Position:
    trading_symbol: str
    exchange:      str
    product:       str
    quantity:      int         # net qty (positive = long, negative = short)
    buy_qty:       int
    sell_qty:      int
    avg_price:     float
    ltp:           float
    pnl:           float
    realised_pnl:  float
    unrealised_pnl: float

    @property
    def side(self) -> str:
        return "LONG" if self.quantity >= 0 else "SHORT"

    @classmethod
    def from_dict(cls, d: dict) -> "Position":
        return cls(
            trading_symbol  = d.get("trdSym", ""),
            exchange        = d.get("exSeg", ""),
            product         = d.get("prod", ""),
            quantity        = int(d.get("flBuyQty", 0) or 0) - int(d.get("flSellQty", 0) or 0),
            buy_qty         = int(d.get("flBuyQty", 0) or 0),
            sell_qty        = int(d.get("flSellQty", 0) or 0),
            avg_price       = float(d.get("buyAvgPrc", 0) or 0),
            ltp             = float(d.get("ltp", 0) or 0),
            pnl             = float(d.get("pnl", 0) or 0),
            realised_pnl    = float(d.get("realPnl", 0) or 0),
            unrealised_pnl  = float(d.get("unrealPnl", 0) or 0),
        )


# ---------------------------------------------------------------------------
# Holding
# ---------------------------------------------------------------------------

@dataclass
class Holding:
    trading_symbol: str
    isin:          str
    quantity:      int
    avg_price:     float
    ltp:           float
    current_value: float
    pnl:           float
    pnl_pct:       float

    @classmethod
    def from_dict(cls, d: dict) -> "Holding":
        qty       = int(d.get("qty", 0) or 0)
        avg_price = float(d.get("avgPrc", 0) or 0)
        ltp       = float(d.get("ltp", 0) or 0)
        cur_val   = qty * ltp
        pnl       = cur_val - (qty * avg_price)
        pnl_pct   = (pnl / (qty * avg_price) * 100) if qty and avg_price else 0.0
        return cls(
            trading_symbol = d.get("trdSym", ""),
            isin           = d.get("isin", ""),
            quantity       = qty,
            avg_price      = avg_price,
            ltp            = ltp,
            current_value  = cur_val,
            pnl            = pnl,
            pnl_pct        = pnl_pct,
        )


# ---------------------------------------------------------------------------
# Margin
# ---------------------------------------------------------------------------

@dataclass
class Margin:
    available_cash:   float
    used_margin:      float
    available_margin: float
    total_equity:     float

    @classmethod
    def from_dict(cls, d: dict) -> "Margin":
        return cls(
            available_cash   = float(d.get("netAvailableMargin", d.get("cash", 0)) or 0),
            used_margin      = float(d.get("utilizedMargin", 0) or 0),
            available_margin = float(d.get("netAvailableMargin", 0) or 0),
            total_equity     = float(d.get("totalEquity", d.get("totalBalance", 0)) or 0),
        )


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------

@dataclass
class Quote:
    trading_symbol: str
    exchange:      str
    ltp:           float
    open:          float
    high:          float
    low:           float
    close:         float
    volume:        int
    bid:           float = 0.0
    ask:           float = 0.0
    change:        float = 0.0
    change_pct:    float = 0.0

    @classmethod
    def from_dict(cls, d: dict) -> "Quote":
        ltp   = float(d.get("ltp", d.get("lastPrice", 0)) or 0)
        close = float(d.get("close", d.get("closePrice", 0)) or 0)
        chg   = ltp - close
        chg_p = (chg / close * 100) if close else 0.0
        return cls(
            trading_symbol = d.get("trdSym", d.get("symbol", "")),
            exchange       = d.get("exSeg", d.get("exchange", "")),
            ltp            = ltp,
            open           = float(d.get("open", d.get("openPrice", 0)) or 0),
            high           = float(d.get("high", d.get("highPrice", 0)) or 0),
            low            = float(d.get("low", d.get("lowPrice", 0)) or 0),
            close          = close,
            volume         = int(d.get("volume", d.get("vol", 0)) or 0),
            bid            = float(d.get("bid", 0) or 0),
            ask            = float(d.get("ask", d.get("offer", 0)) or 0),
            change         = chg,
            change_pct     = chg_p,
        )


# ---------------------------------------------------------------------------
# GTT Order
# ---------------------------------------------------------------------------

@dataclass
class GTTOrder:
    """
    Good Till Triggered order.
    Stays active until the trigger price is hit,
    then automatically places a limit/market order.
    """
    exchange:       Exchange
    trading_symbol: str
    side:           OrderSide
    trigger_price:  float        # price at which the order activates
    limit_price:    float        # execution price (use 0 for market execution)
    quantity:       int
    product:        ProductType  = ProductType.CNC
    order_type:     OrderType    = OrderType.LIMIT
    gtt_id:         str          = ""   # filled on creation

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "exchange":        self.exchange.value,
            "tradingSymbol":   self.trading_symbol,
            "transactionType": self.side.value,
            "triggerPrice":    str(self.trigger_price),
            "price":           str(self.limit_price),
            "quantity":        str(self.quantity),
            "product":         self.product.value,
            "orderType":       self.order_type.value,
        }


# ---------------------------------------------------------------------------
# Basket Order
# ---------------------------------------------------------------------------

@dataclass
class BasketOrder:
    """
    A named collection of orders submitted in a single API call.
    Useful for multi-leg option strategies (straddles, spreads, etc.)
    """
    name:   str
    orders: list[Order]

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "basketName": self.name,
            "orders":     [o.to_api_dict() for o in self.orders],
        }
