"""Paper Trading Broker - Simulated trading without real money."""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from brokers.abstract_broker import AbstractBroker, BrokerOrder, BrokerOrderResponse, BrokerPosition, BrokerBalance, BrokerError
import uuid

logger = logging.getLogger(__name__)


class PaperTradingBroker(AbstractBroker):
    """Paper (simulated) trading broker for learning and backtesting."""
    
    def __init__(self):
        super().__init__("paper")
        self.is_connected = True
        
        # Simulated account
        self.balance = 100000.0  # ₹100k starting balance
        self.positions: Dict[str, BrokerPosition] = {}
        self.orders: Dict[str, BrokerOrderResponse] = {}
        self.closed_orders: List[BrokerOrderResponse] = []
        
        # Market data (mock)
        self.quotes: Dict[str, Dict] = {}
    
    def authenticate(self, credentials: Dict[str, str]) -> Tuple[bool, str]:
        """Paper trading doesn't need authentication."""
        self.is_connected = True
        logger.info("✅ Paper Trading Broker Ready")
        return True, "Paper trading initialized with ₹100,000"
    
    def _get_mock_quote(self, symbol: str) -> Dict[str, float]:
        """Get mock quote for symbol."""
        import random
        
        # Return cached quote or generate new one
        if symbol not in self.quotes:
            # Base prices for common stocks
            base_prices = {
                'RELIANCE': 2389.50,
                'TCS': 3500.00,
                'INFY': 1800.00,
                'HDFCBANK': 1650.00,
                'ICICIBANK': 950.00,
                'SBIN': 650.00,
                'WIPRO': 420.00,
                'LT': 2300.00,
                'ASIANPAINT': 3100.00,
                'MARUTI': 9500.00,
            }
            
            ltp = base_prices.get(symbol, 1000.0)
            # Random walk for more realistic prices
            ltp += random.uniform(-10, 10)
        else:
            ltp = self.quotes[symbol]['ltp']
        
        self.quotes[symbol] = {
            'ltp': ltp,
            'bid': ltp - 0.1,
            'ask': ltp + 0.1,
            'high': ltp + 50,
            'low': ltp - 50,
            'open': ltp - 20,
            'close': ltp,
            'volume': 1000000
        }
        
        return self.quotes[symbol]
    
    def get_quote(self, symbol: str) -> Dict[str, float]:
        """Get quote for single symbol."""
        return self._get_mock_quote(symbol)
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Get quotes for multiple symbols."""
        return {symbol: self._get_mock_quote(symbol) for symbol in symbols}
    
    def place_order(self, order: BrokerOrder) -> Tuple[bool, str, Optional[str]]:
        """
        Place paper order (simulated execution).
        
        For MARKET orders: Execute immediately at current LTP
        For LIMIT orders: Queue order, simulate execution
        """
        try:
            quote = self.get_quote(order.symbol)
            order_id = f"PAPER_{uuid.uuid4().hex[:8]}"
            
            # Calculate order value
            if order.order_type == 'MARKET':
                exec_price = quote['ltp']
            else:
                exec_price = order.price
            
            order_value = exec_price * order.quantity
            
            # Check margin
            if order_value > self.balance:
                return False, f"Insufficient margin. Need ₹{order_value:.0f}, have ₹{self.balance:.0f}", None
            
            # Create order record
            broker_order = BrokerOrderResponse(
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                status='EXECUTED',  # Paper trading executes instantly
                filled_qty=order.quantity,
                avg_price=exec_price,
                timestamp=datetime.now()
            )
            
            self.orders[order_id] = broker_order
            
            # Update positions
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                
                if order.side == 'BUY':
                    # Add to position
                    new_qty = pos.quantity + order.quantity
                    new_avg_price = (pos.avg_price * pos.quantity + exec_price * order.quantity) / new_qty
                    
                    pos.quantity = new_qty
                    pos.avg_price = new_avg_price
                else:
                    # Reduce position
                    pos.quantity -= order.quantity
                    if pos.quantity == 0:
                        del self.positions[order.symbol]
            else:
                # New position
                self.positions[order.symbol] = BrokerPosition(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    avg_price=exec_price,
                    current_price=exec_price,
                    pnl=0,
                    pnl_pct=0,
                    side='LONG' if order.side == 'BUY' else 'SHORT'
                )
            
            # Update balance
            if order.side == 'BUY':
                self.balance -= order_value
            else:
                self.balance += order_value
            
            logger.info(f"📝 [PAPER] {order.side} {order.quantity} {order.symbol} @ ₹{exec_price:.2f} (ID: {order_id})")
            return True, "Order placed and executed (paper trading)", order_id
        
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return False, str(e), None
    
    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        """Cancel order (only if not executed)."""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status == 'EXECUTED':
                return False, "Cannot cancel executed order"
            
            order.status = 'CANCELLED'
            logger.info(f"✅ Order cancelled: {order_id}")
            return True, "Order cancelled"
        
        return False, f"Order not found: {order_id}"
    
    def get_orders(self, status: Optional[str] = None) -> List[BrokerOrderResponse]:
        """Get list of orders."""
        orders = list(self.orders.values())
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        return orders
    
    def get_positions(self) -> List[BrokerPosition]:
        """Get open positions with updated P&L."""
        for symbol, pos in self.positions.items():
            quote = self.get_quote(symbol)
            current_price = quote['ltp']
            
            if pos.side == 'LONG':
                pnl = (current_price - pos.avg_price) * pos.quantity
            else:
                pnl = (pos.avg_price - current_price) * pos.quantity
            
            pnl_pct = (pnl / (pos.avg_price * pos.quantity)) * 100 if pos.avg_price > 0 else 0
            
            pos.current_price = current_price
            pos.pnl = pnl
            pos.pnl_pct = pnl_pct
        
        return list(self.positions.values())
    
    def get_balance(self) -> BrokerBalance:
        """Get account balance."""
        # Calculate total position value
        total_position_value = 0
        for pos in self.positions.values():
            total_position_value += pos.current_price * pos.quantity
        
        total_equity = self.balance + total_position_value
        used_margin = total_position_value
        
        return BrokerBalance(
            available_cash=self.balance,
            used_margin=used_margin,
            available_margin=self.balance,
            total_equity=total_equity,
            product_balance={
                'MIS': self.balance * 0.5,  # Mock allocation
                'CNC': self.balance * 0.5
            }
        )
    
    def get_historical_data(self, symbol: str, interval: str, 
                           start_date: str, end_date: str) -> Dict:
        """Generate mock historical data."""
        import random
        from datetime import datetime as dt, timedelta
        
        # Generate 30 days of mock candles
        base_price = self._get_mock_quote(symbol)['ltp']
        
        timestamps = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        current_date = dt.fromisoformat(start_date)
        end = dt.fromisoformat(end_date)
        
        price = base_price
        while current_date <= end:
            if current_date.weekday() < 5:  # Skip weekends
                o = price + random.uniform(-10, 10)
                h = o + random.uniform(5, 30)
                l = o - random.uniform(5, 30)
                c = price + random.uniform(-20, 20)
                
                timestamps.append(current_date.isoformat())
                opens.append(o)
                highs.append(h)
                lows.append(l)
                closes.append(c)
                volumes.append(random.randint(100000, 5000000))
                
                price = c
            
            current_date += timedelta(days=1)
        
        return {
            'timestamp': timestamps,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }
