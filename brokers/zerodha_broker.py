"""Zerodha Kite API Implementation."""

import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from brokers.abstract_broker import AbstractBroker, BrokerOrder, BrokerOrderResponse, BrokerPosition, BrokerBalance, BrokerError

logger = logging.getLogger(__name__)


class ZerodhaBroker(AbstractBroker):
    """Zerodha Kite API broker implementation."""
    
    def __init__(self):
        super().__init__("zerodha")
        self.base_url = "https://api.kite.trade"
        self.access_token = None
        self.user_id = None
        self.session = None
    
    def authenticate(self, credentials: Dict[str, str]) -> Tuple[bool, str]:
        """
        Authenticate using access token (from https://kite.zerodha.com/connect/login).
        
        Credentials required:
        - access_token: Zerodha auth token (get from OAuth)
        
        For manual setup:
        1. Go to https://kite.zerodha.com/connect/login
        2. Login and copy access_token
        3. Paste here
        """
        try:
            access_token = credentials.get('access_token')
            
            if not access_token:
                return False, "access_token required for Zerodha"
            
            self.access_token = access_token
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'Bearer {access_token}',
                'X-Kite-Version': '3'
            })
            
            # Test authentication
            response = self.session.get(f"{self.base_url}/user/profile")
            
            if response.status_code == 200:
                data = response.json()['data']
                self.user_id = data.get('user_id')
                self.is_connected = True
                logger.info(f"✅ Connected to Zerodha: {self.user_id}")
                return True, f"Connected as {self.user_id}"
            else:
                return False, f"Authentication failed: {response.text}"
        
        except Exception as e:
            logger.error(f"Zerodha auth error: {e}")
            return False, str(e)
    
    def get_quote(self, symbol: str) -> Dict[str, float]:
        """Get quote for single symbol."""
        try:
            if not self.is_connected:
                raise BrokerError("Not connected to Zerodha")
            
            # Get instrument token
            instrument_key = f"NSE:{symbol}"
            
            response = self.session.get(
                f"{self.base_url}/quote",
                params={'i': instrument_key}
            )
            
            if response.status_code == 200:
                data = response.json()['data'][instrument_key]
                return {
                    'ltp': data['last_price'],
                    'bid': data['bid'],
                    'ask': data['ask'],
                    'high': data['high'],
                    'low': data['low'],
                    'open': data['open'],
                    'close': data['close'],
                    'volume': data['volume']
                }
            else:
                raise BrokerError(f"Failed to get quote: {response.text}")
        
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            raise
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Get quotes for multiple symbols."""
        try:
            if not self.is_connected:
                raise BrokerError("Not connected to Zerodha")
            
            instrument_keys = [f"NSE:{s}" for s in symbols]
            
            response = self.session.get(
                f"{self.base_url}/quote",
                params={'i': ','.join(instrument_keys)}
            )
            
            if response.status_code == 200:
                data = response.json()['data']
                quotes = {}
                
                for symbol, key in zip(symbols, instrument_keys):
                    if key in data:
                        d = data[key]
                        quotes[symbol] = {
                            'ltp': d['last_price'],
                            'bid': d['bid'],
                            'ask': d['ask'],
                            'high': d['high'],
                            'low': d['low'],
                            'volume': d['volume']
                        }
                
                return quotes
            else:
                raise BrokerError(f"Failed to get quotes: {response.text}")
        
        except Exception as e:
            logger.error(f"Error getting quotes: {e}")
            raise
    
    def place_order(self, order: BrokerOrder) -> Tuple[bool, str, Optional[str]]:
        """Place order on Zerodha."""
        try:
            if not self.is_connected:
                raise BrokerError("Not connected to Zerodha")
            
            payload = {
                'variety': 'regular',
                'tradingsymbol': order.symbol,
                'exchange': 'NSE',
                'transaction_type': order.side,
                'order_type': 'MARKET' if order.order_type == 'MARKET' else 'LIMIT',
                'quantity': order.quantity,
                'price': order.price if order.order_type == 'LIMIT' else 0,
                'product': order.product,
                'validity': order.validity,
                'tag': 'autotrader'
            }
            
            if order.order_type in ['SL-M', 'SL-L']:
                payload['trigger_price'] = order.trigger_price or 0
            
            response = self.session.post(
                f"{self.base_url}/orders/place",
                data=payload
            )
            
            if response.status_code == 200:
                order_id = response.json()['data']['order_id']
                logger.info(f"✅ Order placed on Zerodha: {order_id}")
                return True, "Order placed successfully", order_id
            else:
                return False, f"Order failed: {response.text}", None
        
        except Exception as e:
            logger.error(f"Error placing order on Zerodha: {e}")
            return False, str(e), None
    
    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        """Cancel order."""
        try:
            if not self.is_connected:
                raise BrokerError("Not connected to Zerodha")
            
            response = self.session.delete(
                f"{self.base_url}/orders/regular/{order_id}",
                data={'variety': 'regular'}
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
            if not self.is_connected:
                raise BrokerError("Not connected to Zerodha")
            
            response = self.session.get(f"{self.base_url}/orders")
            
            if response.status_code == 200:
                orders = []
                for o in response.json()['data']:
                    if status and o['status'] != status:
                        continue
                    
                    orders.append(BrokerOrderResponse(
                        order_id=o['order_id'],
                        symbol=o['tradingsymbol'],
                        side=o['transaction_type'],
                        quantity=o['quantity'],
                        status=o['status'],
                        filled_qty=o['filled_quantity'],
                        avg_price=o['average_price'],
                        timestamp=datetime.fromisoformat(o['order_timestamp'])
                    ))
                
                return orders
            else:
                raise BrokerError(f"Failed to get orders: {response.text}")
        
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def get_positions(self) -> List[BrokerPosition]:
        """Get open positions."""
        try:
            if not self.is_connected:
                raise BrokerError("Not connected to Zerodha")
            
            response = self.session.get(f"{self.base_url}/portfolio/positions")
            
            if response.status_code == 200:
                positions = []
                for p in response.json()['data']['net']:
                    pnl = p['pnl']
                    pnl_pct = (pnl / (p['buy_value'] + p['sell_value'])) * 100 if (p['buy_value'] + p['sell_value']) > 0 else 0
                    
                    positions.append(BrokerPosition(
                        symbol=p['tradingsymbol'],
                        quantity=p['quantity'],
                        avg_price=p['average_price'],
                        current_price=p['last_price'],
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        side='LONG' if p['quantity'] > 0 else 'SHORT'
                    ))
                
                return positions
            else:
                raise BrokerError(f"Failed to get positions: {response.text}")
        
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_balance(self) -> BrokerBalance:
        """Get account balance."""
        try:
            if not self.is_connected:
                raise BrokerError("Not connected to Zerodha")
            
            response = self.session.get(f"{self.base_url}/user/margins")
            
            if response.status_code == 200:
                data = response.json()['data']['equity']
                
                return BrokerBalance(
                    available_cash=data['available'],
                    used_margin=data['used'],
                    available_margin=data['available'],
                    total_equity=data['equity'],
                    product_balance={
                        'CNC': data.get('cnc_closing_balance', 0),
                        'MIS': data.get('intraday_payin', 0)
                    }
                )
            else:
                raise BrokerError(f"Failed to get balance: {response.text}")
        
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            # Return empty balance
            return BrokerBalance(0, 0, 0, 0, {})
    
    def get_historical_data(self, symbol: str, interval: str, 
                           start_date: str, end_date: str) -> Dict:
        """Get historical OHLCV data."""
        try:
            if not self.is_connected:
                raise BrokerError("Not connected to Zerodha")
            
            instrument_key = f"NSE:{symbol}"
            
            response = self.session.get(
                f"{self.base_url}/instruments/historical/{instrument_key}/{interval}",
                params={'from': start_date, 'to': end_date}
            )
            
            if response.status_code == 200:
                data = response.json()['data']['candles']
                
                return {
                    'timestamp': [d[0] for d in data],
                    'open': [d[1] for d in data],
                    'high': [d[2] for d in data],
                    'low': [d[3] for d in data],
                    'close': [d[4] for d in data],
                    'volume': [d[5] for d in data]
                }
            else:
                raise BrokerError(f"Failed to get historical data: {response.text}")
        
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return {}
