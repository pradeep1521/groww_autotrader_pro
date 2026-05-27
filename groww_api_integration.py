"""Real Groww API Integration - Live trading with Groww broker."""

import requests
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import time

logger = logging.getLogger(__name__)

@dataclass
class GrowwOrder:
    """Groww order structure."""
    symbol: str
    side: str  # BUY/SELL
    qty: int
    price: float
    order_type: str  # MARKET/LIMIT/SL-M/SL-L
    product: str  # MIS/CNC/NRML
    trigger_price: Optional[float] = None
    disclosed_qty: int = 0
    validity: str = "DAY"

class GrowwAPIClient:
    """Real Groww Broker API client."""
    
    def __init__(self, client_id: str, client_secret: str, 
                 username: str, password: str, 
                 base_url: str = "https://api.groww.in"):
        """
        Initialize Groww API client.
        
        Args:
            client_id: Groww application client ID
            client_secret: Groww application secret
            username: Groww trading account username
            password: Groww trading account password
            base_url: Groww API base URL
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.base_url = base_url
        self.access_token = None
        self.token_expires = None
        self.session = requests.Session()
        self.user_id = None
        
        logger.info("✅ Groww API client initialized")
    
    def authenticate(self) -> bool:
        """Authenticate with Groww servers and get access token."""
        
        try:
            # Step 1: Generate request signature
            timestamp = str(int(time.time() * 1000))
            auth_string = f"{self.client_id}:{timestamp}"
            
            signature = hashlib.sha256(
                f"{auth_string}:{self.client_secret}".encode()
            ).hexdigest()
            
            # Step 2: Login
            login_payload = {
                'clientid': self.client_id,
                'username': self.username,
                'password': self.password,
                'timestamp': timestamp,
                'signature': signature
            }
            
            response = self.session.post(
                f"{self.base_url}/v1/auth/login",
                json=login_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('accessToken')
                self.user_id = data.get('userId')
                self.token_expires = datetime.now() + timedelta(hours=23)  # 24h validity
                
                logger.info(f"✅ Authenticated with Groww: {self.user_id}")
                return True
            else:
                logger.error(f"❌ Groww auth failed: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Groww authentication error: {e}")
            return False
    
    def _ensure_authenticated(self) -> bool:
        """Ensure valid authentication token."""
        
        if not self.access_token or (self.token_expires and datetime.now() > self.token_expires):
            return self.authenticate()
        return True
    
    def place_order(self, order: GrowwOrder, paper_mode: bool = True) -> Dict[str, Any]:
        """Place order on Groww."""
        
        if not self._ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}
        
        try:
            # Prepare order payload
            payload = {
                'symbol': order.symbol,
                'side': order.side,
                'quantity': order.qty,
                'price': order.price,
                'orderType': order.order_type,
                'product': order.product,
                'triggerPrice': order.trigger_price or 0,
                'disclosedQuantity': order.disclosed_qty,
                'validity': order.validity,
                'userId': self.user_id
            }
            
            if paper_mode:
                # Mock order placement
                logger.info(f"📝 [PAPER] Order: {order.side} {order.qty} {order.symbol} @ ₹{order.price}")
                return {
                    'success': True,
                    'orderId': f"MOCK_{datetime.now().timestamp()}",
                    'symbol': order.symbol,
                    'status': 'PENDING',
                    'message': 'Paper trading order'
                }
            
            # Real order
            response = self.session.post(
                f"{self.base_url}/v1/orders/place",
                json=payload,
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Order placed: {data.get('orderId')}")
                return {'success': True, 'data': data}
            else:
                logger.error(f"❌ Order placement failed: {response.text}")
                return {'success': False, 'error': response.text}
        
        except Exception as e:
            logger.error(f"❌ Order placement error: {e}")
            return {'success': False, 'error': str(e)}
    
    def cancel_order(self, order_id: str, symbol: str = None, paper_mode: bool = True) -> Dict[str, Any]:
        """Cancel existing order."""
        
        if not self._ensure_authenticated():
            return {'success': False, 'error': 'Authentication failed'}
        
        try:
            if paper_mode:
                logger.info(f"📝 [PAPER] Cancel order: {order_id}")
                return {'success': True, 'message': 'Paper order cancelled'}
            
            response = self.session.post(
                f"{self.base_url}/v1/orders/{order_id}/cancel",
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Order cancelled: {order_id}")
                return {'success': True}
            else:
                logger.error(f"❌ Cancel failed: {response.text}")
                return {'success': False, 'error': response.text}
        
        except Exception as e:
            logger.error(f"❌ Cancel error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_positions(self, paper_mode: bool = True) -> List[Dict[str, Any]]:
        """Get open positions."""
        
        if not self._ensure_authenticated():
            return []
        
        try:
            if paper_mode:
                return []  # Mock empty positions
            
            response = self.session.get(
                f"{self.base_url}/v1/positions",
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('data', [])
            else:
                logger.error(f"❌ Get positions failed: {response.text}")
                return []
        
        except Exception as e:
            logger.error(f"❌ Get positions error: {e}")
            return []
    
    def get_orders(self, paper_mode: bool = True) -> List[Dict[str, Any]]:
        """Get order history."""
        
        if not self._ensure_authenticated():
            return []
        
        try:
            if paper_mode:
                return []  # Mock empty orders
            
            response = self.session.get(
                f"{self.base_url}/v1/orders",
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('data', [])
            else:
                logger.error(f"❌ Get orders failed: {response.text}")
                return []
        
        except Exception as e:
            logger.error(f"❌ Get orders error: {e}")
            return []
    
    def get_account_balance(self, paper_mode: bool = True) -> Dict[str, float]:
        """Get account balance and buying power."""
        
        if not self._ensure_authenticated():
            return {}
        
        try:
            if paper_mode:
                return {'balance': 500000, 'buying_power': 500000, 'used_margin': 0}
            
            response = self.session.get(
                f"{self.base_url}/v1/account/balance",
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                return {
                    'balance': float(data.get('balance', 0)),
                    'buying_power': float(data.get('buyingPower', 0)),
                    'used_margin': float(data.get('usedMargin', 0))
                }
            else:
                logger.error(f"❌ Get balance failed: {response.text}")
                return {}
        
        except Exception as e:
            logger.error(f"❌ Get balance error: {e}")
            return {}
    
    def get_quote(self, symbol: str) -> Dict[str, float]:
        """Get live market quote."""
        
        try:
            response = self.session.get(
                f"{self.base_url}/v1/quotes/{symbol}",
                headers={'Authorization': f'Bearer {self.access_token}'} if self.access_token else {},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json().get('data', {})
                return {
                    'ltp': float(data.get('ltp', 0)),
                    'open': float(data.get('open', 0)),
                    'high': float(data.get('high', 0)),
                    'low': float(data.get('low', 0)),
                    'close': float(data.get('close', 0)),
                    'volume': int(data.get('volume', 0))
                }
            else:
                logger.error(f"❌ Quote failed: {response.text}")
                return {}
        
        except Exception as e:
            logger.error(f"❌ Quote error: {e}")
            return {}

class GrowwTradingSystem:
    """High-level trading system using Groww API."""
    
    def __init__(self, api_client: GrowwAPIClient):
        self.api = api_client
        self.paper_mode = True
    
    def execute_trade(self, symbol: str, side: str, qty: int, 
                     order_type: str = "MARKET", price: float = None) -> Dict[str, Any]:
        """Execute a trade."""
        
        order = GrowwOrder(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price or 0,
            order_type=order_type,
            product="MIS"  # Margin Intraday Square-off
        )
        
        return self.api.place_order(order, paper_mode=self.paper_mode)
    
    def place_sl_order(self, symbol: str, trigger_price: float, 
                      qty: int = 1) -> Dict[str, Any]:
        """Place stop-loss order."""
        
        order = GrowwOrder(
            symbol=symbol,
            side="SELL",
            qty=qty,
            price=0,
            order_type="SL-M",  # Stop-Loss Market
            trigger_price=trigger_price,
            product="MIS"
        )
        
        return self.api.place_order(order, paper_mode=self.paper_mode)
    
    def get_portfolio_pnl(self) -> Dict[str, float]:
        """Calculate portfolio P&L."""
        
        positions = self.api.get_positions(paper_mode=self.paper_mode)
        
        total_pnl = 0
        total_pnl_pct = 0
        
        for pos in positions:
            pnl = float(pos.get('pnl', 0))
            pnl_pct = float(pos.get('pnlPct', 0))
            total_pnl += pnl
            total_pnl_pct += pnl_pct
        
        return {
            'total_pnl': total_pnl,
            'avg_pnl_pct': total_pnl_pct / len(positions) if positions else 0,
            'positions': len(positions)
        }

# Example usage
def example_groww_trading():
    """Example Groww API trading."""
    
    api = GrowwAPIClient(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        username="your_username",
        password="your_password"
    )
    
    # Enable paper mode for safety
    system = GrowwTradingSystem(api)
    system.paper_mode = True
    
    # Place order
    print("Placing order...")
    result = system.execute_trade(
        symbol="NIFTY50",
        side="BUY",
        qty=1,
        order_type="MARKET"
    )
    print(f"Order result: {result}")
    
    # Get balance
    print("\nGetting account balance...")
    balance = api.get_account_balance(paper_mode=True)
    print(f"Balance: {balance}")
    
    print("\n✅ Groww API integration complete!")

if __name__ == "__main__":
    example_groww_trading()
