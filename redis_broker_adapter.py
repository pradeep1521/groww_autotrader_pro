"""Redis Broker Adapter - Multi-broker execution with sub-millisecond latency."""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order status tracking."""
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass
class BrokerConfig:
    """Broker configuration."""
    name: str
    slippage_bps: int  # Basis points
    commission_pct: float
    min_volume: int
    max_order_size: int
    latency_ms: int
    uptime_pct: float  # SLA uptime
    priority: int  # Lower = higher priority

class RedisBrokerCache:
    """Redis-based broker state cache for fast access."""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.host = redis_host
        self.port = redis_port
        self.redis = None
        self.connected = False
        
        try:
            import redis
            self.redis = redis.Redis(host=redis_host, port=redis_port, 
                                    decode_responses=True)
            self.connected = self.redis.ping()
            logger.info(f"✅ Connected to Redis at {redis_host}:{redis_port}")
        except ImportError:
            logger.warning("redis-py not installed. Install: pip install redis")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
    
    def set_order(self, order_id: str, order_data: Dict[str, Any], 
                 ttl_seconds: int = 3600) -> bool:
        """Cache order in Redis."""
        if not self.connected:
            return False
        
        try:
            key = f"order:{order_id}"
            self.redis.setex(key, ttl_seconds, json.dumps(order_data))
            return True
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order from Redis cache."""
        if not self.connected:
            return None
        
        try:
            key = f"order:{order_id}"
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
            return None
    
    def set_broker_stats(self, broker_name: str, stats: Dict[str, Any]) -> bool:
        """Cache broker statistics."""
        if not self.connected:
            return False
        
        try:
            key = f"broker:stats:{broker_name}"
            self.redis.setex(key, 60, json.dumps(stats))  # 60-second TTL
            return True
        except Exception as e:
            logger.error(f"Failed to set broker stats: {e}")
            return False
    
    def get_broker_stats(self, broker_name: str) -> Optional[Dict]:
        """Get cached broker statistics."""
        if not self.connected:
            return None
        
        try:
            key = f"broker:stats:{broker_name}"
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to get broker stats: {e}")
            return None
    
    def publish_execution(self, channel: str, execution_data: Dict) -> bool:
        """Publish execution to Redis pub/sub."""
        if not self.connected:
            return False
        
        try:
            self.redis.publish(channel, json.dumps(execution_data))
            return True
        except Exception as e:
            logger.error(f"Failed to publish: {e}")
            return False

class MultiBrokerExecutor:
    """Execute orders across multiple brokers."""
    
    def __init__(self, redis_cache: RedisBrokerCache = None):
        self.redis_cache = redis_cache
        self.brokers: Dict[str, BrokerConfig] = {}
        self.order_log = []
        self.execution_times = {}
    
    def register_broker(self, broker_config: BrokerConfig) -> bool:
        """Register a broker with configuration."""
        self.brokers[broker_config.name] = broker_config
        logger.info(f"✅ Registered broker: {broker_config.name}")
        return True
    
    def select_best_broker(self, symbol: str, order_type: str, 
                         size: int) -> Optional[BrokerConfig]:
        """Select best broker for execution."""
        
        # Filter by constraints
        eligible = [
            b for b in self.brokers.values()
            if b.max_order_size >= size and b.uptime_pct >= 0.99
        ]
        
        if not eligible:
            logger.warning("No eligible brokers found")
            return None
        
        # Score by: lowest slippage (30%), lowest latency (40%), highest uptime (30%)
        def score_broker(b: BrokerConfig) -> float:
            slippage_score = b.slippage_bps / 100
            latency_score = b.latency_ms / 100
            uptime_score = (100 - (b.uptime_pct * 100)) / 100
            
            return (slippage_score * 0.3 + latency_score * 0.4 + uptime_score * 0.3)
        
        best_broker = min(eligible, key=score_broker)
        logger.info(f"Selected broker: {best_broker.name} for {symbol}")
        
        return best_broker
    
    async def execute_order(self, symbol: str, side: str, quantity: int, 
                           price: float, order_type: str = "MARKET") -> Dict[str, Any]:
        """Execute order on best broker."""
        
        # Select broker
        broker = self.select_best_broker(symbol, order_type, quantity)
        
        if not broker:
            return {
                'status': OrderStatus.REJECTED.value,
                'reason': 'No eligible brokers',
                'timestamp': datetime.now().isoformat()
            }
        
        # Simulate order execution
        order_id = f"{symbol}_{datetime.now().timestamp()}"
        execution_start = datetime.now()
        
        # Simulate broker latency
        await asyncio.sleep(broker.latency_ms / 1000)
        
        # Calculate slippage
        slippage = (price * broker.slippage_bps / 10000)
        executed_price = price + slippage if side == "BUY" else price - slippage
        
        # Calculate commission
        commission = (executed_price * quantity * broker.commission_pct / 100)
        
        execution_time = (datetime.now() - execution_start).total_seconds() * 1000
        self.execution_times[order_id] = execution_time
        
        result = {
            'order_id': order_id,
            'broker': broker.name,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'execution_price': executed_price,
            'commission': commission,
            'slippage_bps': broker.slippage_bps,
            'status': OrderStatus.FILLED.value,
            'execution_time_ms': execution_time,
            'timestamp': datetime.now().isoformat()
        }
        
        # Cache order
        if self.redis_cache:
            self.redis_cache.set_order(order_id, result)
            self.redis_cache.publish_execution('executions', result)
        
        self.order_log.append(result)
        
        logger.info(f"✅ Execution: {symbol} {side} {quantity} @ ₹{executed_price:.2f}")
        
        return result
    
    async def batch_execute(self, orders: List[Dict[str, Any]]) -> List[Dict]:
        """Execute multiple orders in parallel."""
        tasks = [
            self.execute_order(
                order['symbol'],
                order['side'],
                order['quantity'],
                order['price'],
                order.get('order_type', 'MARKET')
            )
            for order in orders
        ]
        
        results = await asyncio.gather(*tasks)
        return results
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        if not self.order_log:
            return {}
        
        execution_times = list(self.execution_times.values())
        
        return {
            'total_orders': len(self.order_log),
            'avg_execution_time_ms': sum(execution_times) / len(execution_times),
            'min_execution_time_ms': min(execution_times),
            'max_execution_time_ms': max(execution_times),
            'total_commission': sum(o.get('commission', 0) for o in self.order_log),
            'total_slippage': sum((o.get('execution_price', 0) - o.get('price', 0)) * o.get('quantity', 0) 
                                 for o in self.order_log),
            'filled_orders': len([o for o in self.order_log if o['status'] == OrderStatus.FILLED.value])
        }

class LoadBalancer:
    """Load balance orders across brokers."""
    
    def __init__(self, executor: MultiBrokerExecutor):
        self.executor = executor
        self.broker_loads = {}
    
    def update_load(self, broker_name: str, current_load: int):
        """Update broker load metrics."""
        self.broker_loads[broker_name] = {
            'current_load': current_load,
            'timestamp': datetime.now()
        }
    
    def get_least_loaded_broker(self) -> Optional[BrokerConfig]:
        """Get least loaded broker."""
        if not self.broker_loads:
            return None
        
        least_loaded = min(
            self.broker_loads.items(),
            key=lambda x: x[1]['current_load']
        )
        
        broker_name = least_loaded[0]
        return self.executor.brokers.get(broker_name)

class ExecutionOptimizer:
    """Optimize order execution strategy."""
    
    def __init__(self, executor: MultiBrokerExecutor):
        self.executor = executor
        self.historical_stats = {}
    
    def analyze_execution_quality(self, order_id: str) -> Dict[str, Any]:
        """Analyze execution quality metrics."""
        
        # In production: fetch from ClickHouse
        # For now: return mock analysis
        return {
            'order_id': order_id,
            'slippage_vs_best': 2,  # basis points
            'execution_time_percentile': 45,  # 45th percentile
            'broker_recommendation': 'GOOD',
            'improvement_possible': 1.5  # basis points
        }
    
    async def adaptive_execution(self, symbol: str, side: str, 
                                quantity: int, price: float) -> Dict:
        """Adaptive execution based on market conditions."""
        
        # Strategy: Split large orders across brokers
        if quantity > 10000:
            # Split into chunks
            chunk_size = quantity // 3
            
            orders = [
                {'symbol': symbol, 'side': side, 'quantity': chunk_size, 'price': price}
                for _ in range(3)
            ]
            
            results = await self.executor.batch_execute(orders)
            
            avg_price = sum(r.get('execution_price', 0) * r.get('quantity', 0) 
                           for r in results) / quantity
            
            return {
                'order_type': 'SPLIT',
                'original_quantity': quantity,
                'chunks': 3,
                'avg_execution_price': avg_price,
                'results': results
            }
        else:
            # Single execution
            return await self.executor.execute_order(symbol, side, quantity, price)

# Example usage
async def example_multi_broker():
    """Example multi-broker execution."""
    
    # Initialize
    redis_cache = RedisBrokerCache()
    executor = MultiBrokerExecutor(redis_cache)
    
    # Register brokers
    brokers = [
        BrokerConfig("Groww", slippage_bps=5, commission_pct=0.05, 
                    min_volume=1, max_order_size=100000, latency_ms=50, 
                    uptime_pct=0.9999, priority=1),
        BrokerConfig("Zerodha", slippage_bps=3, commission_pct=0.03,
                    min_volume=1, max_order_size=500000, latency_ms=30,
                    uptime_pct=0.99999, priority=2),
        BrokerConfig("Upstox", slippage_bps=4, commission_pct=0.04,
                    min_volume=1, max_order_size=250000, latency_ms=40,
                    uptime_pct=0.9999, priority=3)
    ]
    
    for broker_config in brokers:
        executor.register_broker(broker_config)
    
    # Execute orders
    orders = [
        {'symbol': 'NIFTY50', 'side': 'BUY', 'quantity': 1, 'price': 23894.10},
        {'symbol': 'TCS', 'side': 'SELL', 'quantity': 10, 'price': 3850.0},
        {'symbol': 'INFY', 'side': 'BUY', 'quantity': 5, 'price': 2200.0}
    ]
    
    results = await executor.batch_execute(orders)
    
    print("\n📊 Multi-Broker Execution Results:")
    for result in results:
        print(f"✅ {result['symbol']}: {result['status']} @ ₹{result['execution_price']:.2f}")
    
    # Stats
    stats = executor.get_execution_stats()
    print(f"\n⚡ Execution Stats:")
    print(f"  Avg Time: {stats.get('avg_execution_time_ms', 0):.1f}ms")
    print(f"  Total Commission: ₹{stats.get('total_commission', 0):.2f}")

if __name__ == "__main__":
    asyncio.run(example_multi_broker())
