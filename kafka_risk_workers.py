"""Kafka Risk Workers - Distributed real-time risk monitoring."""

import json
import logging
from typing import Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class RiskEventType(Enum):
    """Types of risk events."""
    DELTA_BREACH = "DELTA_BREACH"
    GAMMA_RISK = "GAMMA_RISK"
    THETA_DECAY = "THETA_DECAY"
    VEGA_SPIKE = "VEGA_SPIKE"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    MARGIN_WARNING = "MARGIN_WARNING"
    CORRELATION_BREAK = "CORRELATION_BREAK"
    IV_EXTREME = "IV_EXTREME"

@dataclass
class RiskEvent:
    """Structured risk event."""
    event_type: RiskEventType
    timestamp: datetime
    strategy_id: str
    severity: str  # INFO, WARNING, CRITICAL
    message: str
    metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'strategy_id': self.strategy_id,
            'severity': self.severity,
            'message': self.message,
            'metrics': self.metrics
        }

class KafkaRiskWorker:
    """Kafka-based distributed risk monitoring worker."""
    
    def __init__(self, broker_urls: List[str] = None, group_id: str = "risk-monitoring"):
        self.broker_urls = broker_urls or ['localhost:9092']
        self.group_id = group_id
        self.producer = None
        self.consumer = None
        self.running = False
        self.event_handlers = {}
        
        try:
            from kafka import KafkaProducer, KafkaConsumer
            self.KafkaProducer = KafkaProducer
            self.KafkaConsumer = KafkaConsumer
            self.kafka_available = True
        except ImportError:
            logger.warning("kafka-python not installed. Install: pip install kafka-python")
            self.kafka_available = False
    
    def connect(self) -> bool:
        """Connect to Kafka broker."""
        if not self.kafka_available:
            logger.warning("Kafka not available - running in mock mode")
            return False
        
        try:
            self.producer = self.KafkaProducer(
                bootstrap_servers=self.broker_urls,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            logger.info(f"✅ Connected to Kafka at {self.broker_urls}")
            return True
        except Exception as e:
            logger.error(f"❌ Kafka connection failed: {e}")
            return False
    
    def publish_risk_event(self, event: RiskEvent, topic: str = "risk-events") -> bool:
        """Publish risk event to Kafka."""
        if not self.producer:
            logger.warning("Kafka producer not available")
            return False
        
        try:
            future = self.producer.send(topic, value=event.to_dict())
            # Wait for message to be sent
            future.get(timeout=10)
            logger.debug(f"📤 Published {event.event_type.value} event")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to publish event: {e}")
            return False
    
    def subscribe_to_events(self, topics: List[str], callback: Callable):
        """Subscribe to risk events."""
        if not self.kafka_available:
            logger.warning("Kafka not available")
            return
        
        try:
            self.consumer = self.KafkaConsumer(
                *topics,
                bootstrap_servers=self.broker_urls,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            self.running = True
            logger.info(f"📩 Subscribed to topics: {topics}")
            
            for message in self.consumer:
                try:
                    event_data = message.value
                    callback(event_data)
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
        
        except Exception as e:
            logger.error(f"❌ Subscription failed: {e}")

class PortfolioRiskWorker:
    """Analyze portfolio-level Greeks and risk."""
    
    def __init__(self, kafka_worker: KafkaRiskWorker = None):
        self.kafka = kafka_worker
        self.portfolio_greeks = {
            'delta': 0,
            'gamma': 0,
            'theta': 0,
            'vega': 0,
            'rho': 0
        }
        self.limits = {
            'max_delta': 0.3,
            'max_gamma': 0.05,
            'min_theta': 0.5,
            'max_vega': 100
        }
    
    def update_greeks(self, positions: List[Dict[str, float]]) -> Dict[str, float]:
        """Calculate portfolio Greeks from positions."""
        self.portfolio_greeks = {
            'delta': sum(p.get('delta', 0) for p in positions),
            'gamma': sum(p.get('gamma', 0) for p in positions),
            'theta': sum(p.get('theta', 0) for p in positions),
            'vega': sum(p.get('vega', 0) for p in positions),
            'rho': sum(p.get('rho', 0) for p in positions)
        }
        
        return self.portfolio_greeks
    
    def check_risk_breaches(self, strategy_id: str) -> List[RiskEvent]:
        """Check for Greeks limit breaches."""
        events = []
        
        # Delta breach
        if abs(self.portfolio_greeks['delta']) > self.limits['max_delta']:
            events.append(RiskEvent(
                event_type=RiskEventType.DELTA_BREACH,
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                severity='WARNING',
                message=f"Delta {self.portfolio_greeks['delta']:.4f} exceeds limit {self.limits['max_delta']}",
                metrics=self.portfolio_greeks
            ))
        
        # Gamma risk
        if abs(self.portfolio_greeks['gamma']) > self.limits['max_gamma']:
            events.append(RiskEvent(
                event_type=RiskEventType.GAMMA_RISK,
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                severity='CRITICAL',
                message=f"Gamma {self.portfolio_greeks['gamma']:.6f} exceeds limit",
                metrics=self.portfolio_greeks
            ))
        
        # Theta decay
        if self.portfolio_greeks['theta'] < self.limits['min_theta']:
            events.append(RiskEvent(
                event_type=RiskEventType.THETA_DECAY,
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                severity='INFO',
                message=f"Theta {self.portfolio_greeks['theta']:.4f} is low",
                metrics=self.portfolio_greeks
            ))
        
        # Vega exposure
        if abs(self.portfolio_greeks['vega']) > self.limits['max_vega']:
            events.append(RiskEvent(
                event_type=RiskEventType.VEGA_SPIKE,
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                severity='WARNING',
                message=f"Vega {self.portfolio_greeks['vega']:.2f} exceeds limit",
                metrics=self.portfolio_greeks
            ))
        
        return events

class DailyLossWorker:
    """Monitor daily loss limits."""
    
    def __init__(self, daily_loss_limit: float = 25000):
        self.daily_loss_limit = daily_loss_limit
        self.daily_pnl = 0
        self.trades_today = []
    
    def add_trade(self, trade: Dict[str, Any]):
        """Add trade to daily tracking."""
        self.trades_today.append(trade)
        self.daily_pnl += trade.get('pnl', 0)
    
    def check_daily_loss_breach(self, strategy_id: str) -> List[RiskEvent]:
        """Check if daily loss limit is breached."""
        events = []
        
        if self.daily_pnl <= -self.daily_loss_limit:
            events.append(RiskEvent(
                event_type=RiskEventType.DAILY_LOSS_LIMIT,
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                severity='CRITICAL',
                message=f"Daily loss ₹{abs(self.daily_pnl):.0f} exceeds limit ₹{self.daily_loss_limit:.0f}",
                metrics={'daily_pnl': self.daily_pnl, 'limit': self.daily_loss_limit}
            ))
        elif self.daily_pnl <= -self.daily_loss_limit * 0.8:
            events.append(RiskEvent(
                event_type=RiskEventType.DAILY_LOSS_LIMIT,
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                severity='WARNING',
                message=f"Daily loss ₹{abs(self.daily_pnl):.0f} at 80% of limit",
                metrics={'daily_pnl': self.daily_pnl, 'limit': self.daily_loss_limit}
            ))
        
        return events
    
    def reset_daily(self):
        """Reset daily tracking."""
        self.daily_pnl = 0
        self.trades_today = []

class CorrelationRiskWorker:
    """Monitor correlation breaks and contagion risk."""
    
    def __init__(self, correlation_threshold: float = 0.7):
        self.correlation_threshold = correlation_threshold
        self.price_data = {}
    
    def update_prices(self, symbol: str, price: float):
        """Update price data."""
        self.price_data[symbol] = price
    
    def check_correlation_break(self, symbol_pair: tuple, historical_correlation: float) -> List[RiskEvent]:
        """Check if correlation has broken."""
        events = []
        
        sym1, sym2 = symbol_pair
        
        if sym1 not in self.price_data or sym2 not in self.price_data:
            return events
        
        # Simplified correlation check (in production: use proper correlation calculation)
        price1 = self.price_data[sym1]
        price2 = self.price_data[sym2]
        
        # Mock correlation check
        current_corr = 0.5  # Placeholder
        
        if abs(current_corr - historical_correlation) > 0.3:
            events.append(RiskEvent(
                event_type=RiskEventType.CORRELATION_BREAK,
                timestamp=datetime.now(),
                strategy_id="correlation-worker",
                severity='WARNING',
                message=f"Correlation between {sym1}-{sym2} changed from {historical_correlation:.2f} to {current_corr:.2f}",
                metrics={'symbol_pair': symbol_pair, 'historical_corr': historical_correlation, 'current_corr': current_corr}
            ))
        
        return events

class IVWorker:
    """Monitor implied volatility extremes."""
    
    def __init__(self, iv_percentile_threshold: float = 0.9):
        self.iv_threshold = iv_percentile_threshold
        self.iv_history = {}
    
    def update_iv(self, symbol: str, iv: float, iv_percentile: float):
        """Update IV data."""
        if symbol not in self.iv_history:
            self.iv_history[symbol] = []
        
        self.iv_history[symbol].append({
            'iv': iv,
            'percentile': iv_percentile,
            'timestamp': datetime.now()
        })
    
    def check_iv_extreme(self, symbol: str, strategy_id: str) -> List[RiskEvent]:
        """Check for IV extremes."""
        events = []
        
        if symbol not in self.iv_history or not self.iv_history[symbol]:
            return events
        
        latest = self.iv_history[symbol][-1]
        
        if latest['percentile'] > self.iv_threshold:
            events.append(RiskEvent(
                event_type=RiskEventType.IV_EXTREME,
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                severity='WARNING',
                message=f"IV percentile for {symbol} at {latest['percentile']*100:.1f}% (extreme high)",
                metrics={'symbol': symbol, 'iv': latest['iv'], 'percentile': latest['percentile']}
            ))
        elif latest['percentile'] < (1 - self.iv_threshold):
            events.append(RiskEvent(
                event_type=RiskEventType.IV_EXTREME,
                timestamp=datetime.now(),
                strategy_id=strategy_id,
                severity='INFO',
                message=f"IV percentile for {symbol} at {latest['percentile']*100:.1f}% (extreme low)",
                metrics={'symbol': symbol, 'iv': latest['iv'], 'percentile': latest['percentile']}
            ))
        
        return events

class RiskAggregator:
    """Aggregate risk from all workers."""
    
    def __init__(self, kafka_worker: KafkaRiskWorker = None):
        self.kafka = kafka_worker
        self.workers = []
        self.all_events: List[RiskEvent] = []
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    def register_worker(self, worker):
        """Register a risk worker."""
        self.workers.append(worker)
    
    def aggregate_risk(self, strategy_id: str) -> List[RiskEvent]:
        """Aggregate risk from all workers."""
        events = []
        
        for worker in self.workers:
            if hasattr(worker, 'check_risk_breaches'):
                events.extend(worker.check_risk_breaches(strategy_id))
            elif hasattr(worker, 'check_daily_loss_breach'):
                events.extend(worker.check_daily_loss_breach(strategy_id))
        
        self.all_events.extend(events)
        
        # Publish to Kafka
        if self.kafka:
            for event in events:
                self.kafka.publish_risk_event(event)
        
        return events
    
    def get_critical_events(self) -> List[RiskEvent]:
        """Get only critical events."""
        return [e for e in self.all_events if e.severity == 'CRITICAL']

# Example usage
def example_kafka_monitoring():
    """Example Kafka-based monitoring."""
    # Initialize workers
    kafka_worker = KafkaRiskWorker(['localhost:9092'])
    
    portfolio_worker = PortfolioRiskWorker(kafka_worker)
    daily_loss_worker = DailyLossWorker(daily_loss_limit=25000)
    iv_worker = IVWorker()
    
    # Sample positions
    positions = [
        {'delta': 0.25, 'gamma': 0.012, 'theta': 0.35, 'vega': -25, 'rho': -5},
        {'delta': -0.10, 'gamma': 0.008, 'theta': 0.20, 'vega': -15, 'rho': -3}
    ]
    
    # Update portfolio Greeks
    greeks = portfolio_worker.update_greeks(positions)
    print(f"📊 Portfolio Greeks: {greeks}")
    
    # Check for breaches
    events = portfolio_worker.check_risk_breaches("STRATEGY_001")
    print(f"⚠️ Risk events: {len(events)}")
    
    # Monitor daily loss
    daily_loss_worker.add_trade({'pnl': -5000})
    daily_loss_worker.add_trade({'pnl': -8000})
    
    loss_events = daily_loss_worker.check_daily_loss_breach("STRATEGY_001")
    print(f"💰 Daily loss warning: {len(loss_events)} events")

if __name__ == "__main__":
    example_kafka_monitoring()
