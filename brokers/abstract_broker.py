"""
Abstract Broker Interface - Base class for all brokers.
Ensures consistent API across different brokers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BrokerOrder:
    """Input order object for placing orders."""
    symbol: str
    side: str  # BUY/SELL
    quantity: int
    price: float
    order_type: str  # MARKET/LIMIT/SL-M/SL-L
    product: str = "MIS"  # MIS/CNC/NRML
    trigger_price: Optional[float] = None
    validity: str = "DAY"
    disclosed_qty: int = 0
    order_id: Optional[str] = None  # Optional - set by broker


@dataclass
class BrokerOrderResponse:
    """Response order object returned by broker."""
    order_id: str
    symbol: str
    side: str
    quantity: int
    status: str  # PENDING/EXECUTED/REJECTED/CANCELLED
    filled_qty: int
    avg_price: float
    timestamp: datetime


@dataclass
class BrokerPosition:
    """Standard position structure."""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    pnl: float
    pnl_pct: float
    side: str  # LONG/SHORT
    exchange: str = "NSE"


@dataclass
class BrokerBalance:
    """Standard account balance."""
    available_cash: float
    used_margin: float
    available_margin: float
    total_equity: float
    product_balance: Dict[str, float]  # MIS/CNC/NRML balances


class AbstractBroker(ABC):
    """Abstract base class for all broker implementations."""
    
    def __init__(self, broker_name: str):
        self.broker_name = broker_name
        self.is_connected = False
    
    @abstractmethod
    def authenticate(self, credentials: Dict[str, str]) -> Tuple[bool, str]:
        """
        Authenticate with broker.
        
        Returns: (success, message)
        """
        pass
    
    @abstractmethod
    def get_quote(self, symbol: str) -> Dict[str, float]:
        """
        Get current LTP for symbol.
        
        Returns: {'ltp': 100.5, 'bid': 100.4, 'ask': 100.6, ...}
        """
        pass
    
    @abstractmethod
    def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Get current quotes for multiple symbols.
        
        Returns: {
            'RELIANCE': {'ltp': 2389.50, 'bid': 2389.40, ...},
            'TCS': {'ltp': 3500.00, ...},
            ...
        }
        """
        pass
    
    @abstractmethod
    def place_order(self, order: BrokerOrder) -> Tuple[bool, str, Optional[str]]:
        """
        Place order on broker.
        
        Returns: (success, message, order_id)
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        """
        Cancel existing order.
        
        Returns: (success, message)
        """
        pass
    
    @abstractmethod
    def get_orders(self, status: Optional[str] = None) -> List[BrokerOrder]:
        """
        Get list of orders.
        
        Args:
            status: PENDING/EXECUTED/REJECTED/CANCELLED (None = all)
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[BrokerPosition]:
        """Get list of open positions."""
        pass
    
    @abstractmethod
    def get_balance(self) -> BrokerBalance:
        """Get account balance and margin details."""
        pass
    
    @abstractmethod
    def get_historical_data(self, symbol: str, interval: str, 
                           start_date: str, end_date: str) -> Dict:
        """
        Get historical OHLCV data.
        
        Args:
            symbol: Stock symbol
            interval: '1m', '5m', '15m', '1h', '1d'
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
        
        Returns: {
            'timestamp': [...],
            'open': [...],
            'high': [...],
            'low': [...],
            'close': [...],
            'volume': [...]
        }
        """
        pass
    
    def get_broker_name(self) -> str:
        """Get broker name."""
        return self.broker_name
    
    def is_market_open(self) -> bool:
        """Check if market is open (IST timezone)."""
        from datetime import datetime
        now = datetime.now()
        
        # Market hours: 09:15 - 15:30 (IST)
        # Closed: Saturday, Sunday
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        market_open = now.replace(hour=9, minute=15, second=0)
        market_close = now.replace(hour=15, minute=30, second=0)
        
        return market_open <= now <= market_close


class BrokerError(Exception):
    """Custom exception for broker errors."""
    pass
