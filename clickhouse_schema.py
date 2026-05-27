"""ClickHouse Schema Definition - OLAP Data Warehouse for Trading."""

from typing import Dict, List, Any
import json
from datetime import datetime

class ClickHouseSchema:
    """Define and manage ClickHouse tables for institutional trading."""
    
    # Table 1: Market Data (OLAP optimized)
    MARKET_DATA_TABLE = """
    CREATE TABLE IF NOT EXISTS market_data (
        timestamp DateTime,
        symbol String,
        open Float32,
        high Float32,
        low Float32,
        close Float32,
        volume UInt64,
        vwap Float32,
        bid Float32,
        ask Float32,
        bid_size UInt32,
        ask_size UInt32,
        iv_percentile Float32,
        put_call_ratio Float32,
        date Date DEFAULT toDate(timestamp),
        hour UInt8 DEFAULT toHour(timestamp)
    ) ENGINE = MergeTree()
    ORDER BY (date, symbol, timestamp)
    PARTITION BY toYYYYMM(date)
    TTL date + INTERVAL 2 YEAR
    SETTINGS index_granularity = 8192
    """
    
    # Table 2: Options Chain Data
    OPTIONS_CHAIN_TABLE = """
    CREATE TABLE IF NOT EXISTS options_chain (
        timestamp DateTime,
        symbol String,
        strike Float32,
        expiry_date Date,
        option_type Enum('CALL' = 1, 'PUT' = 2),
        bid Float32,
        ask Float32,
        last_price Float32,
        volume UInt32,
        open_interest UInt32,
        iv Float32,
        delta Float32,
        gamma Float32,
        theta Float32,
        vega Float32,
        rho Float32,
        dte UInt8,
        moneyness Float32,
        date Date DEFAULT toDate(timestamp)
    ) ENGINE = MergeTree()
    ORDER BY (date, symbol, strike, option_type, timestamp)
    PARTITION BY toYYYYMM(date)
    TTL date + INTERVAL 1 YEAR
    SETTINGS index_granularity = 8192
    """
    
    # Table 3: Trade Execution Log
    TRADES_TABLE = """
    CREATE TABLE IF NOT EXISTS trades (
        trade_id UUID DEFAULT generateUUIDv4(),
        timestamp DateTime,
        strategy_id String,
        symbol String,
        side Enum('BUY' = 1, 'SELL' = 2),
        order_type Enum('MARKET' = 1, 'LIMIT' = 2, 'SL_M' = 3),
        entry_price Float32,
        entry_quantity UInt32,
        exit_price Float32 DEFAULT 0,
        exit_time DateTime DEFAULT now(),
        pnl Float32,
        pnl_pct Float32,
        slippage_bps UInt16,
        commission Float32,
        entry_iv Float32,
        exit_iv Float32,
        max_profit Float32,
        max_loss Float32,
        duration_seconds UInt32,
        status Enum('OPEN' = 1, 'CLOSED' = 2, 'CANCELLED' = 3),
        date Date DEFAULT toDate(timestamp),
        hour UInt8 DEFAULT toHour(timestamp)
    ) ENGINE = MergeTree()
    ORDER BY (date, strategy_id, symbol, timestamp)
    PARTITION BY toYYYYMM(date)
    TTL date + INTERVAL 5 YEAR
    SETTINGS index_granularity = 8192
    """
    
    # Table 4: Portfolio Greeks (Time-series)
    PORTFOLIO_GREEKS_TABLE = """
    CREATE TABLE IF NOT EXISTS portfolio_greeks (
        timestamp DateTime,
        strategy_id String,
        portfolio_delta Float32,
        portfolio_gamma Float32,
        portfolio_theta Float32,
        portfolio_vega Float32,
        portfolio_rho Float32,
        max_delta_limit Float32,
        current_exposure_pct Float32,
        margin_used Float32,
        margin_available Float32,
        daily_pnl Float32,
        max_drawdown_pct Float32,
        date Date DEFAULT toDate(timestamp),
        hour UInt8 DEFAULT toHour(timestamp)
    ) ENGINE = MergeTree()
    ORDER BY (date, strategy_id, timestamp)
    PARTITION BY toYYYYMM(date)
    TTL date + INTERVAL 2 YEAR
    SETTINGS index_granularity = 4096
    """
    
    # Table 5: Risk Events Log
    RISK_EVENTS_TABLE = """
    CREATE TABLE IF NOT EXISTS risk_events (
        event_id UUID DEFAULT generateUUIDv4(),
        timestamp DateTime,
        strategy_id String,
        event_type Enum('LIMIT_BREACH' = 1, 'MARGIN_CALL' = 2, 'IV_SPIKE' = 3, 
                       'GAMMA_RISK' = 4, 'THETA_DECAY' = 5, 'POSITION_CLOSED' = 6),
        severity Enum('INFO' = 1, 'WARNING' = 2, 'CRITICAL' = 3),
        message String,
        delta_breach Float32 DEFAULT 0,
        gamma_breach Float32 DEFAULT 0,
        theta_value Float32 DEFAULT 0,
        vega_exposure Float32 DEFAULT 0,
        action_taken String,
        date Date DEFAULT toDate(timestamp)
    ) ENGINE = MergeTree()
    ORDER BY (date, strategy_id, severity, timestamp)
    PARTITION BY toYYYYMM(date)
    TTL date + INTERVAL 1 YEAR
    SETTINGS index_granularity = 4096
    """
    
    # Table 6: Strategy Performance Analytics
    STRATEGY_PERFORMANCE_TABLE = """
    CREATE TABLE IF NOT EXISTS strategy_performance (
        date Date,
        strategy_id String,
        total_trades UInt32,
        winning_trades UInt32,
        losing_trades UInt32,
        win_rate Float32,
        total_pnl Float32,
        max_daily_pnl Float32,
        min_daily_pnl Float32,
        avg_pnl_per_trade Float32,
        max_drawdown_pct Float32,
        sharpe_ratio Float32,
        profit_factor Float32,
        avg_trade_duration UInt32,
        cumulative_return_pct Float32
    ) ENGINE = MergeTree()
    ORDER BY (date, strategy_id)
    PARTITION BY toYYYYMM(date)
    TTL date + INTERVAL 5 YEAR
    SETTINGS index_granularity = 8192
    """
    
    # Table 7: Tick Data (High-frequency)
    TICK_DATA_TABLE = """
    CREATE TABLE IF NOT EXISTS tick_data (
        timestamp DateTime,
        symbol String,
        bid Float32,
        ask Float32,
        bid_size UInt32,
        ask_size UInt32,
        last_trade_price Float32,
        last_trade_size UInt32,
        volume UInt64,
        date Date DEFAULT toDate(timestamp),
        minute DateTime DEFAULT toStartOfMinute(timestamp)
    ) ENGINE = MergeTree()
    ORDER BY (date, symbol, timestamp)
    PARTITION BY toYYYYMM(date)
    TTL date + INTERVAL 90 DAY  # Keep only 90 days of tick data
    SETTINGS index_granularity = 1024
    """

class ClickHouseConnector:
    """Interface for ClickHouse operations."""
    
    def __init__(self, host: str = "localhost", port: int = 9000, 
                 database: str = "trading", username: str = "default", password: str = ""):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.connection = None
    
    def connect(self) -> bool:
        """Connect to ClickHouse."""
        try:
            from clickhouse_driver import Client
            self.connection = Client(
                self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password
            )
            # Test connection
            result = self.connection.execute('SELECT 1')
            print(f"✅ Connected to ClickHouse at {self.host}:{self.port}")
            return True
        except ImportError:
            print("⚠️ clickhouse-driver not installed. Install: pip install clickhouse-driver")
            return False
        except Exception as e:
            print(f"❌ ClickHouse connection failed: {e}")
            return False
    
    def create_tables(self) -> bool:
        """Create all required tables."""
        if not self.connection:
            print("❌ Not connected to ClickHouse")
            return False
        
        tables = [
            ClickHouseSchema.MARKET_DATA_TABLE,
            ClickHouseSchema.OPTIONS_CHAIN_TABLE,
            ClickHouseSchema.TRADES_TABLE,
            ClickHouseSchema.PORTFOLIO_GREEKS_TABLE,
            ClickHouseSchema.RISK_EVENTS_TABLE,
            ClickHouseSchema.STRATEGY_PERFORMANCE_TABLE,
            ClickHouseSchema.TICK_DATA_TABLE
        ]
        
        try:
            for table_sql in tables:
                self.connection.execute(table_sql)
            print("✅ All ClickHouse tables created successfully")
            return True
        except Exception as e:
            print(f"❌ Table creation failed: {e}")
            return False
    
    def insert_market_data(self, data: Dict[str, Any]) -> bool:
        """Insert market data."""
        if not self.connection:
            return False
        
        try:
            query = """
            INSERT INTO market_data 
            (timestamp, symbol, open, high, low, close, volume, vwap, bid, ask)
            VALUES
            """
            values = [
                (
                    data['timestamp'],
                    data['symbol'],
                    data['open'],
                    data['high'],
                    data['low'],
                    data['close'],
                    data['volume'],
                    data.get('vwap', data['close']),
                    data.get('bid', data['close']),
                    data.get('ask', data['close'])
                )
            ]
            self.connection.execute(query, values)
            return True
        except Exception as e:
            print(f"❌ Market data insertion failed: {e}")
            return False
    
    def insert_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Insert trade record."""
        if not self.connection:
            return False
        
        try:
            query = """
            INSERT INTO trades 
            (timestamp, strategy_id, symbol, side, order_type, entry_price, 
             entry_quantity, exit_price, pnl, pnl_pct, commission, status)
            VALUES
            """
            values = [(
                trade_data['timestamp'],
                trade_data['strategy_id'],
                trade_data['symbol'],
                trade_data['side'],
                trade_data['order_type'],
                trade_data['entry_price'],
                trade_data['entry_quantity'],
                trade_data.get('exit_price', 0),
                trade_data.get('pnl', 0),
                trade_data.get('pnl_pct', 0),
                trade_data.get('commission', 0),
                'OPEN'
            )]
            self.connection.execute(query, values)
            return True
        except Exception as e:
            print(f"❌ Trade insertion failed: {e}")
            return False
    
    def query_market_data(self, symbol: str, days: int = 30) -> List[Dict]:
        """Query historical market data."""
        if not self.connection:
            return []
        
        try:
            query = f"""
            SELECT timestamp, symbol, open, high, low, close, volume
            FROM market_data
            WHERE symbol = '{symbol}' AND date >= today() - {days}
            ORDER BY timestamp DESC
            LIMIT 1000
            """
            result = self.connection.execute(query)
            return [dict(zip(['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'], row)) 
                   for row in result]
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return []
    
    def get_daily_pnl(self, strategy_id: str, date: str) -> float:
        """Get daily P&L for strategy."""
        if not self.connection:
            return 0
        
        try:
            query = f"""
            SELECT SUM(pnl) as total_pnl
            FROM trades
            WHERE strategy_id = '{strategy_id}' AND date = '{date}' AND status = 'CLOSED'
            """
            result = self.connection.execute(query)
            return result[0][0] if result else 0
        except Exception as e:
            print(f"❌ P&L query failed: {e}")
            return 0
    
    def get_strategy_analytics(self, strategy_id: str, days: int = 30) -> Dict:
        """Get strategy performance analytics."""
        if not self.connection:
            return {}
        
        try:
            query = f"""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as max_win,
                MIN(pnl) as max_loss
            FROM trades
            WHERE strategy_id = '{strategy_id}' AND date >= today() - {days}
            """
            result = self.connection.execute(query)
            if result:
                row = result[0]
                return {
                    'total_trades': row[0],
                    'winning_trades': row[1],
                    'losing_trades': row[2],
                    'total_pnl': row[3],
                    'avg_pnl': row[4],
                    'max_win': row[5],
                    'max_loss': row[6]
                }
        except Exception as e:
            print(f"❌ Analytics query failed: {e}")
        
        return {}

# Example usage
if __name__ == "__main__":
    # Initialize ClickHouse
    ch = ClickHouseConnector()
    
    if ch.connect():
        ch.create_tables()
        
        # Insert sample market data
        sample_data = {
            'timestamp': datetime.now(),
            'symbol': 'NIFTY50',
            'open': 23850.0,
            'high': 23950.0,
            'low': 23800.0,
            'close': 23894.10,
            'volume': 5000000,
            'vwap': 23880.0,
            'bid': 23893.0,
            'ask': 23895.0
        }
        
        if ch.insert_market_data(sample_data):
            print("✅ Sample data inserted")
    
    print("\n📊 ClickHouse Schema:")
    print("✅ market_data - Real-time + historical prices")
    print("✅ options_chain - Greeks + IV data")
    print("✅ trades - Trade execution log")
    print("✅ portfolio_greeks - Time-series Greeks")
    print("✅ risk_events - Risk monitoring log")
    print("✅ strategy_performance - Daily analytics")
    print("✅ tick_data - High-frequency ticks (90-day retention)")
