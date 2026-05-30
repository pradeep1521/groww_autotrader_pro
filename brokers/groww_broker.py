"""Groww Broker API Implementation."""

import requests
import logging
import hashlib
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from brokers.abstract_broker import AbstractBroker, BrokerOrder, BrokerOrderResponse, BrokerPosition, BrokerBalance, BrokerError

logger = logging.getLogger(__name__)


class GrowwBrokerImpl(AbstractBroker):
    """Groww Broker API implementation."""
    
    def __init__(self):
        super().__init__("groww")
        self.base_url = "https://api.groww.in"
        self.access_token = None
        self.user_id = None
        self.session = requests.Session()
        self.token_expires = None
    
    def authenticate(self, credentials: Dict[str, str]) -> Tuple[bool, str]:
        """
        Authenticate with Groww API.
        
        Credentials required (one of):
        - client_id, client_secret, username, password
        - OR access_token (pre-generated)
        """
        try:
            # If access_token provided, use it directly
            if 'access_token' in credentials:
                self.access_token = credentials['access_token']
                self.is_connected = True
                logger.info("✅ Connected to Groww with existing token")
                return True, "Connected to Groww"
            
            # Otherwise, authenticate with credentials
            client_id = credentials.get('client_id')
            client_secret = credentials.get('client_secret')
            username = credentials.get('username')
            password = credentials.get('password')
            
            if not all([client_id, client_secret, username, password]):
                return False, "client_id, client_secret, username, password required"
            
            # Generate signature
            timestamp = str(int(time.time() * 1000))
            auth_string = f"{client_id}:{timestamp}"
            signature = hashlib.sha256(
                f"{auth_string}:{client_secret}".encode()
            ).hexdigest()
            
            # Login
            payload = {
                'clientid': client_id,
                'username': username,
                'password': password,
                'timestamp': timestamp,
                'signature': signature
            }
            
            response = self.session.post(
                f"{self.base_url}/v1/auth/login",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('accessToken')
                self.user_id = data.get('userId')
                self.token_expires = datetime.now() + timedelta(hours=23)
                self.is_connected = True
                
                logger.info(f"✅ Connected to Groww: {self.user_id}")
                return True, f"Connected as {self.user_id}"
            else:
                return False, f"Auth failed: {response.text}"
        
        except Exception as e:
            logger.error(f"Groww auth error: {e}")
            return False, str(e)
    
    def _ensure_authenticated(self) -> bool:
        """Check if token is still valid."""
        if not self.access_token:
            return False
        if self.token_expires and datetime.now() > self.token_expires:
            return False
        return True
    
    def get_quote(self, symbol: str) -> Dict[str, float]:
        """Get quote for single symbol."""
        try:
            if not self._ensure_authenticated():
                raise BrokerError("Not authenticated with Groww")
            
            # Groww API: GET /v1/quotes/{symbol}
            response = self.session.get(
                f"{self.base_url}/v1/quotes/{symbol}",
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()['data']
                return {
                    'ltp': data['ltp'],
                    'bid': data.get('bid', data['ltp']),
                    'ask': data.get('ask', data['ltp']),
                    'high': data.get('high', data['ltp']),
                    'low': data.get('low', data['ltp']),
                    'open': data.get('open', data['ltp']),
                    'close': data.get('close', data['ltp']),
                    'volume': data.get('volume', 0)
                }
            else:
                raise BrokerError(f"Failed to get quote: {response.text}")
        
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            raise
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Get quotes for multiple symbols."""
        quotes = {}
        
        for symbol in symbols:
            try:
                quotes[symbol] = self.get_quote(symbol)
            except Exception as e:
                logger.error(f"Error getting quote for {symbol}: {e}")
                continue
        
        return quotes
    
    def place_order(self, order: BrokerOrder) -> Tuple[bool, str, Optional[str]]:
        """Place order on Groww."""
        try:
            if not self._ensure_authenticated():
                raise BrokerError("Not authenticated with Groww")
            
            payload = {
                'symbol': order.symbol,
                'side': order.side,
                'quantity': order.quantity,
                'price': order.price,
                'orderType': order.order_type,
                'product': order.product,
                'triggerPrice': order.trigger_price or 0,
                'disclosedQuantity': order.disclosed_qty,
                'validity': order.validity
            }
            
            response = self.session.post(
                f"{self.base_url}/v1/orders/place",
                json=payload,
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                order_id = response.json()['data']['orderId']
                logger.info(f"✅ Order placed on Groww: {order_id}")
                return True, "Order placed successfully", order_id
            else:
                return False, f"Order failed: {response.text}", None
        
        except Exception as e:
            logger.error(f"Error placing order on Groww: {e}")
            return False, str(e), None
    
    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        """Cancel order."""
        try:
            if not self._ensure_authenticated():
                raise BrokerError("Not authenticated with Groww")
            
            response = self.session.delete(
                f"{self.base_url}/v1/orders/{order_id}",
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Order cancelled: {order_id}")
                return True, "Order cancelled"
            else:
                return False, f"Cancel failed: {response.text}"
        
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False, str(e)
    
    def get_orders(self, status: Optional[str] = None) -> List[BrokerOrderResponse]:
        """Get list of orders."""
        try:
            if not self._ensure_authenticated():
                raise BrokerError("Not authenticated with Groww")
            
            response = self.session.get(
                f"{self.base_url}/v1/orders",
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                orders = []
                for o in response.json()['data']:
                    if status and o['status'] != status:
                        continue
                    
                    orders.append(BrokerOrderResponse(
                        order_id=o['orderId'],
                        symbol=o['symbol'],
                        side=o['side'],
                        quantity=o['quantity'],
                        status=o['status'],
                        filled_qty=o.get('filledQuantity', 0),
                        avg_price=o.get('averagePrice', 0),
                        timestamp=datetime.fromisoformat(o['orderTime'])
                    ))
                
                return orders
            else:
                return []
        
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def get_positions(self) -> List[BrokerPosition]:
        """Get open positions."""
        try:
            if not self._ensure_authenticated():
                raise BrokerError("Not authenticated with Groww")
            
            response = self.session.get(
                f"{self.base_url}/v1/positions",
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                positions = []
                for p in response.json()['data']:
                    pnl = p['pnl']
                    position_value = p['avgPrice'] * p['quantity']
                    pnl_pct = (pnl / position_value * 100) if position_value > 0 else 0
                    
                    positions.append(BrokerPosition(
                        symbol=p['symbol'],
                        quantity=p['quantity'],
                        avg_price=p['avgPrice'],
                        current_price=p['ltp'],
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        side='LONG' if p['quantity'] > 0 else 'SHORT'
                    ))
                
                return positions
            else:
                return []
        
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_balance(self) -> BrokerBalance:
        """Get account balance."""
        try:
            if not self._ensure_authenticated():
                raise BrokerError("Not authenticated with Groww")
            
            response = self.session.get(
                f"{self.base_url}/v1/account/margin",
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()['data']
                
                return BrokerBalance(
                    available_cash=data['availableCash'],
                    used_margin=data['usedMargin'],
                    available_margin=data['availableMargin'],
                    total_equity=data['totalEquity'],
                    product_balance={
                        'MIS': data.get('misBalance', 0),
                        'CNC': data.get('cncBalance', 0)
                    }
                )
            else:
                return BrokerBalance(0, 0, 0, 0, {})
        
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return BrokerBalance(0, 0, 0, 0, {})
    
    def get_historical_data(self, symbol: str, interval: str, 
                           start_date: str, end_date: str) -> Dict:
        """Get historical OHLCV data."""
        try:
            if not self._ensure_authenticated():
                raise BrokerError("Not authenticated with Groww")
            
            response = self.session.get(
                f"{self.base_url}/v1/historical/{symbol}",
                params={
                    'interval': interval,
                    'startDate': start_date,
                    'endDate': end_date
                },
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()['data']
                
                return {
                    'timestamp': [d['timestamp'] for d in data],
                    'open': [d['open'] for d in data],
                    'high': [d['high'] for d in data],
                    'low': [d['low'] for d in data],
                    'close': [d['close'] for d in data],
                    'volume': [d['volume'] for d in data]
                }
            else:
                return {}
        
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return {}
