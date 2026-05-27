"""
Groww API Broker Wrapper with Retry Logic & Error Handling.
Wraps growwapi with resilience patterns and paper-trade fallback.
"""

import time
from typing import Dict, List, Optional, Tuple
from functools import wraps
import threading

from logger import logger

try:
    from growwapi import GrowwAPI
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False
    logger.warning("growwapi SDK not available. Using paper trading mode.")


def retry_on_exception(max_retries: int = 3, backoff: float = 1.0):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {str(e)}")
                        raise
                    wait_time = backoff * (2 ** attempt)
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        return wrapper
    return decorator


class GrowwBroker:
    """Groww API broker wrapper with robust error handling."""
    
    def __init__(self, access_token: str = "", api_key: str = "", api_secret: str = ""):
        """
        Initialize Groww broker connection.
        Falls back to paper mode if connection fails.
        """
        self._api = None
        self._connected = False
        self._lock = threading.Lock()
        self._mock_positions: Dict[str, dict] = {}
        self._mock_order_id_counter = 1
        
        if not _SDK_AVAILABLE:
            logger.warning("growwapi not installed. Running in paper mode only.")
            return
        
        try:
            if access_token:
                self._api = GrowwAPI(access_token)
            elif api_key and api_secret:
                # Try getting token from credentials
                token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
                self._api = GrowwAPI(token)
            
            if self._api:
                # Test connection
                self._api.get_available_margin_details()
                self._connected = True
                logger.info("✅ Connected to Groww API")
        except Exception as e:
            logger.error(f"Failed to connect to Groww: {str(e)}")
            self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        return self._connected and self._api is not None
    
    @retry_on_exception(max_retries=3, backoff=0.5)
    def get_margin(self) -> Dict[str, float]:
        """Get available margin and balances."""
        if not self.is_connected:
            return {"available": 100000.0, "equity": 100000.0, "fno": 50000.0, "mock": True}
        
        try:
            data = self._api.get_available_margin_details()
            return {
                "available": float(data.get("clear_cash", 0)),
                "equity": float(data.get("equity_margin_details", {}).get("cnc_balance_available", 0)),
                "fno": float(data.get("fno_margin_details", {}).get("future_balance_available", 0)),
                "mock": False,
            }
        except Exception as e:
            logger.error(f"Failed to fetch margin: {str(e)}")
            return {"available": 0.0, "equity": 0.0, "fno": 0.0, "mock": True}
    
    @retry_on_exception(max_retries=2, backoff=0.5)
    def get_ltp(self, *symbols: str, segment: str = "CASH") -> Dict[str, float]:
        """
        Get last traded price for symbols.
        Returns {symbol: price} dict.
        """
        if not symbols:
            return {}
        
        if not self.is_connected:
            # Mock prices for paper trading
            import random
            return {s: 100 + random.uniform(-10, 10) for s in symbols}
        
        try:
            seg = self._api.SEGMENT_CASH if segment.upper() == "CASH" else self._api.SEGMENT_FNO
            syms = tuple(f"NSE_{s}" for s in symbols)
            
            if len(syms) == 1:
                resp = self._api.get_ltp(segment=seg, exchange_trading_symbols=syms[0])
            else:
                resp = self._api.get_ltp(segment=seg, exchange_trading_symbols=syms)
            
            # Parse response and map back to original symbols
            result = {}
            for key, val in resp.items():
                orig_sym = key.replace("NSE_", "") if "NSE_" in key else key
                result[orig_sym] = float(val)
            return result
        except Exception as e:
            logger.error(f"Failed to fetch LTP for {symbols}: {str(e)}")
            return {}
    
    @retry_on_exception(max_retries=2, backoff=0.5)
    def place_market_order(
        self, symbol: str, side: str, quantity: int,
        segment: str = "CASH", product: str = "MIS"
    ) -> Tuple[bool, Dict]:
        """
        Place a market order.
        Returns (success: bool, response: dict)
        """
        try:
            if not self.is_connected:
                # Paper trade
                with self._lock:
                    order_id = f"PAPER_{self._mock_order_id_counter}"
                    self._mock_order_id_counter += 1
                    ltp = self.get_ltp(symbol).get(symbol, 100.0)
                    self._mock_positions[symbol] = {
                        "qty": quantity if side == "BUY" else -quantity,
                        "price": ltp,
                        "order_id": order_id
                    }
                logger.info(f"📝 PAPER ORDER: {side} {quantity} {symbol} @ ₹{ltp}")
                return True, {"order_id": order_id, "status": "SUCCESS", "mock": True}
            
            seg = self._api.SEGMENT_CASH if segment.upper() == "CASH" else self._api.SEGMENT_FNO
            prod = self._get_product_code(product)
            txn = self._api.TRANSACTION_TYPE_BUY if side == "BUY" else self._api.TRANSACTION_TYPE_SELL
            
            resp = self._api.place_order(
                trading_symbol=symbol,
                quantity=int(quantity),
                validity=self._api.VALIDITY_DAY,
                exchange=self._api.EXCHANGE_NSE,
                segment=seg,
                product=prod,
                order_type=self._api.ORDER_TYPE_MARKET,
                transaction_type=txn,
            )
            
            order_id = resp.get("groww_order_id", "")
            logger.info(f"✅ ORDER PLACED: {side} {quantity} {symbol} - ID: {order_id}")
            return True, {"order_id": order_id, "status": "SUCCESS", "mock": False}
        
        except Exception as e:
            logger.error(f"Failed to place market order: {str(e)}")
            return False, {"error": str(e), "status": "FAILED"}
    
    @retry_on_exception(max_retries=2, backoff=0.5)
    def place_limit_order(
        self, symbol: str, side: str, quantity: int, limit_price: float,
        segment: str = "CASH", product: str = "MIS"
    ) -> Tuple[bool, Dict]:
        """
        Place a limit order with slippage protection.
        Returns (success: bool, response: dict)
        """
        try:
            if not self.is_connected:
                # Paper trade
                with self._lock:
                    order_id = f"PAPER_LIM_{self._mock_order_id_counter}"
                    self._mock_order_id_counter += 1
                logger.info(f"📝 PAPER LIMIT ORDER: {side} {quantity} {symbol} @ ₹{limit_price}")
                return True, {"order_id": order_id, "status": "SUCCESS", "mock": True}
            
            seg = self._api.SEGMENT_CASH if segment.upper() == "CASH" else self._api.SEGMENT_FNO
            prod = self._get_product_code(product)
            txn = self._api.TRANSACTION_TYPE_BUY if side == "BUY" else self._api.TRANSACTION_TYPE_SELL
            
            resp = self._api.place_order(
                trading_symbol=symbol,
                quantity=int(quantity),
                validity=self._api.VALIDITY_DAY,
                exchange=self._api.EXCHANGE_NSE,
                segment=seg,
                product=prod,
                order_type=self._api.ORDER_TYPE_LIMIT,
                price=float(limit_price),
                transaction_type=txn,
            )
            
            order_id = resp.get("groww_order_id", "")
            logger.info(f"✅ LIMIT ORDER PLACED: {side} {quantity} {symbol} @ ₹{limit_price} - ID: {order_id}")
            return True, {"order_id": order_id, "status": "SUCCESS", "mock": False}
        
        except Exception as e:
            logger.error(f"Failed to place limit order: {str(e)}")
            return False, {"error": str(e), "status": "FAILED"}
    
    @retry_on_exception(max_retries=2, backoff=0.5)
    def place_sl_order(
        self, symbol: str, side: str, quantity: int, trigger_price: float,
        segment: str = "CASH", product: str = "MIS"
    ) -> Tuple[bool, Dict]:
        """
        Place a stop-loss market order (SL-M).
        Returns (success: bool, response: dict)
        """
        try:
            if not self.is_connected:
                order_id = f"PAPER_SL_{self._mock_order_id_counter}"
                self._mock_order_id_counter += 1
                logger.info(f"📝 PAPER SL ORDER: {side} {quantity} {symbol} @ trigger ₹{trigger_price}")
                return True, {"order_id": order_id, "status": "SUCCESS", "mock": True}
            
            seg = self._api.SEGMENT_CASH if segment.upper() == "CASH" else self._api.SEGMENT_FNO
            prod = self._get_product_code(product)
            txn = self._api.TRANSACTION_TYPE_BUY if side == "BUY" else self._api.TRANSACTION_TYPE_SELL
            
            resp = self._api.place_order(
                trading_symbol=symbol,
                quantity=int(quantity),
                validity=self._api.VALIDITY_DAY,
                exchange=self._api.EXCHANGE_NSE,
                segment=seg,
                product=prod,
                order_type=self._api.ORDER_TYPE_SL_M,
                trigger_price=float(trigger_price),
                transaction_type=txn,
            )
            
            order_id = resp.get("groww_order_id", "")
            logger.info(f"✅ SL ORDER PLACED: {side} {quantity} {symbol} @ trigger ₹{trigger_price} - ID: {order_id}")
            return True, {"order_id": order_id, "status": "SUCCESS", "mock": False}
        
        except Exception as e:
            logger.error(f"Failed to place SL order: {str(e)}")
            return False, {"error": str(e), "status": "FAILED"}
    
    @retry_on_exception(max_retries=2, backoff=0.5)
    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        """Cancel an order. Returns (success: bool, message: str)"""
        try:
            if not self.is_connected:
                logger.info(f"📝 PAPER ORDER CANCELLED: {order_id}")
                return True, "Paper order cancelled"
            
            resp = self._api.cancel_order(order_id=order_id)
            logger.info(f"✅ ORDER CANCELLED: {order_id}")
            return True, "Order cancelled"
        
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {str(e)}")
            return False, str(e)
    
    def _get_product_code(self, product: str):
        """Map product string to growwapi constant."""
        if not self.is_connected:
            return "MIS"
        
        product_map = {
            "MIS": self._api.PRODUCT_MIS,
            "CNC": self._api.PRODUCT_CNC,
            "NRML": self._api.PRODUCT_NRML,
        }
        return product_map.get(product.upper(), self._api.PRODUCT_MIS)
    
    def disconnect(self):
        """Disconnect from Groww."""
        self._api = None
        self._connected = False
        logger.info("Disconnected from Groww")


# Singleton broker instance
_broker_instance: Optional[GrowwBroker] = None


def get_broker(
    access_token: str = "",
    api_key: str = "",
    api_secret: str = ""
) -> GrowwBroker:
    """Get or create broker singleton."""
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = GrowwBroker(access_token, api_key, api_secret)
    return _broker_instance
