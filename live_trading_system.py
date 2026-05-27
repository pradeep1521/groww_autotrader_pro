"""Event-Driven Live Trading System - Real-time execution and risk management."""

import asyncio
from datetime import datetime
from typing import Dict, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue
import json

class EventType(Enum):
    """Event types for event-driven trading."""
    MARKET_DATA = "MARKET_DATA"
    ENTRY_SIGNAL = "ENTRY_SIGNAL"
    EXIT_SIGNAL = "EXIT_SIGNAL"
    ORDER_PLACED = "ORDER_PLACED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    RISK_ALERT = "RISK_ALERT"
    RISK_BREACH = "RISK_BREACH"

@dataclass
class Event:
    """Base event class."""
    event_type: EventType
    timestamp: datetime
    symbol: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'data': self.data
        }

class EventBus:
    """Central event bus for event-driven architecture."""
    
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_log: List[Event] = []
    
    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Subscribe to event type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    def publish(self, event: Event) -> None:
        """Publish event to all subscribers."""
        self.event_log.append(event)
        
        if event.event_type in self.subscribers:
            for handler in self.subscribers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"❌ Event handler error: {e}")
    
    async def publish_async(self, event: Event) -> None:
        """Publish event asynchronously."""
        await asyncio.to_thread(self.publish, event)
    
    def get_event_log(self, symbol: str = None, event_type: EventType = None) -> List[Event]:
        """Get filtered event log."""
        result = self.event_log
        if symbol:
            result = [e for e in result if e.symbol == symbol]
        if event_type:
            result = [e for e in result if e.event_type == event_type]
        return result

class RiskMonitor:
    """Real-time risk monitoring and enforcement."""
    
    def __init__(self, config: Dict, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.open_positions: Dict[int, Dict] = {}
        self.daily_pnl = 0
        self.max_exposure = 0
        
        # Subscribe to position events
        self.event_bus.subscribe(EventType.POSITION_OPENED, self._on_position_opened)
        self.event_bus.subscribe(EventType.POSITION_CLOSED, self._on_position_closed)
        self.event_bus.subscribe(EventType.ORDER_FILLED, self._check_risk_limits)
    
    def _on_position_opened(self, event: Event) -> None:
        """Handle position opened."""
        position_id = event.data.get('position_id')
        self.open_positions[position_id] = {
            'symbol': event.symbol,
            'entry_price': event.data.get('entry_price'),
            'quantity': event.data.get('quantity'),
            'opening_time': event.timestamp
        }
    
    def _on_position_closed(self, event: Event) -> None:
        """Handle position closed."""
        position_id = event.data.get('position_id')
        if position_id in self.open_positions:
            pnl = event.data.get('pnl', 0)
            self.daily_pnl += pnl
            del self.open_positions[position_id]
    
    def _check_risk_limits(self, event: Event) -> None:
        """Check risk limits on order fill."""
        limits = self.config['risk_management']
        
        # Check max open positions
        if len(self.open_positions) >= limits['max_open_positions']:
            risk_event = Event(
                event_type=EventType.RISK_ALERT,
                timestamp=datetime.now(),
                symbol=event.symbol,
                data={'alert': 'Max open positions reached'}
            )
            self.event_bus.publish(risk_event)
        
        # Check daily loss limit
        if self.daily_pnl <= -limits['max_daily_loss']:
            breach_event = Event(
                event_type=EventType.RISK_BREACH,
                timestamp=datetime.now(),
                symbol=event.symbol,
                data={'breach': 'Daily loss limit exceeded', 'daily_pnl': self.daily_pnl}
            )
            self.event_bus.publish(breach_event)
    
    def get_portfolio_greeks(self) -> Dict[str, float]:
        """Calculate portfolio-level Greeks."""
        total_delta = 0
        total_gamma = 0
        total_theta = 0
        total_vega = 0
        
        for position in self.open_positions.values():
            # In production, use actual Greeks calculation
            total_delta += 0.5  # Placeholder
            total_gamma += 0.01
            total_theta += 0.02
            total_vega += 5
        
        return {
            'delta': total_delta,
            'gamma': total_gamma,
            'theta': total_theta,
            'vega': total_vega
        }
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status."""
        limits = self.config['risk_management']
        
        return {
            'open_positions': len(self.open_positions),
            'max_positions_allowed': limits['max_open_positions'],
            'daily_pnl': self.daily_pnl,
            'daily_loss_limit': limits['max_daily_loss'],
            'at_risk': self.daily_pnl <= -limits['max_daily_loss'] * 0.8,
            'greeks': self.get_portfolio_greeks()
        }

class ExecutionEngine:
    """Multi-broker execution with order orchestration."""
    
    def __init__(self, brokers: Dict[str, Any], event_bus: EventBus):
        self.brokers = brokers
        self.event_bus = event_bus
        self.orders: Dict[int, Dict] = {}
        self.order_id_counter = 0
    
    async def place_order(self, symbol: str, side: str, quantity: int, price: float, 
                         order_type: str = "LIMIT") -> int:
        """Place order on best broker."""
        self.order_id_counter += 1
        order_id = self.order_id_counter
        
        # Select broker (in production: lowest slippage, availability, etc.)
        broker_name = self._select_broker(symbol)
        
        self.orders[order_id] = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'order_type': order_type,
            'broker': broker_name,
            'status': 'PENDING'
        }
        
        # Publish order event
        event = Event(
            event_type=EventType.ORDER_PLACED,
            timestamp=datetime.now(),
            symbol=symbol,
            data={
                'order_id': order_id,
                'side': side,
                'quantity': quantity,
                'price': price,
                'broker': broker_name
            }
        )
        self.event_bus.publish(event)
        
        return order_id
    
    def _select_broker(self, symbol: str) -> str:
        """Select best broker for symbol."""
        # In production: implement broker selection algorithm
        return list(self.brokers.keys())[0]
    
    async def cancel_order(self, order_id: int) -> bool:
        """Cancel an order."""
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'CANCELLED'
            return True
        return False
    
    def get_order_status(self, order_id: int) -> Dict:
        """Get order status."""
        return self.orders.get(order_id, {})

class LiveTradingSystem:
    """Unified live trading system orchestrator."""
    
    def __init__(self, strategy_config: Dict, brokers: Dict[str, Any]):
        self.config = strategy_config
        self.event_bus = EventBus()
        self.risk_monitor = RiskMonitor(strategy_config, self.event_bus)
        self.execution_engine = ExecutionEngine(brokers, self.event_bus)
        self.is_running = False
    
    async def start(self) -> None:
        """Start live trading."""
        self.is_running = True
        print("🚀 Live trading system started")
    
    async def stop(self) -> None:
        """Stop live trading."""
        self.is_running = False
        print("⛔ Live trading system stopped")
    
    async def process_market_data(self, symbol: str, price: float, timestamp: datetime) -> None:
        """Process incoming market data."""
        event = Event(
            event_type=EventType.MARKET_DATA,
            timestamp=timestamp,
            symbol=symbol,
            data={'price': price}
        )
        await self.event_bus.publish_async(event)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status."""
        return {
            'is_running': self.is_running,
            'event_log_size': len(self.event_bus.event_log),
            'risk_status': self.risk_monitor.get_risk_status(),
            'open_orders': {oid: o for oid, o in self.execution_engine.orders.items() 
                          if o['status'] == 'PENDING'}
        }

# Example usage
async def example_trading_flow():
    """Example trading flow."""
    config = {
        'risk_management': {
            'max_open_positions': 5,
            'max_daily_loss': 25000
        }
    }
    
    system = LiveTradingSystem(config, brokers={'Groww': None})
    await system.start()
    
    # Simulate market data
    await system.process_market_data('NIFTY50', 23894.10, datetime.now())
    
    # Place order
    order_id = await system.execution_engine.place_order(
        'NIFTY50', 'BUY', 1, 23894.10
    )
    print(f"Order placed: {order_id}")
    
    # Check status
    status = system.get_system_status()
    print(f"System status: {json.dumps(status, indent=2, default=str)}")
    
    await system.stop()

if __name__ == "__main__":
    asyncio.run(example_trading_flow())
