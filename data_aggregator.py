"""Data Aggregation Engine - Fetch, Transform, Load (ETL) for ClickHouse."""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class DataAggregator:
    """Aggregate market data from multiple sources."""
    
    def __init__(self, clickhouse_connector=None):
        self.ch = clickhouse_connector
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.cache = {}
    
    async def fetch_market_data(self, symbol: str, period: str = "1mo", 
                               interval: str = "1h") -> Optional[pd.DataFrame]:
        """Fetch market data from yfinance."""
        try:
            # Convert to NSE format if needed
            ticker = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
            
            df = yf.download(ticker, period=period, interval=interval, 
                           progress=False, threads=False)
            
            if df.empty:
                logger.warning(f"No data for {symbol}")
                return None
            
            # Add derived columns
            df['vwap'] = self._calculate_vwap(df)
            df['symbol'] = symbol
            df['timestamp'] = df.index
            
            return df[['timestamp', 'symbol', 'Open', 'High', 'Low', 'Close', 'Volume', 'vwap']]
        
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    async def fetch_options_chain(self, symbol: str, expiry_date: str) -> Optional[pd.DataFrame]:
        """Fetch options chain data."""
        try:
            # Placeholder for options data fetch
            # In production, integrate with broker API or NSE data
            logger.info(f"Fetching options chain for {symbol} expiry {expiry_date}")
            
            # Return mock data for now
            return pd.DataFrame({
                'strike': np.arange(23700, 24100, 100),
                'call_bid': np.random.uniform(100, 300, 5),
                'call_ask': np.random.uniform(100, 300, 5),
                'put_bid': np.random.uniform(50, 200, 5),
                'put_ask': np.random.uniform(50, 200, 5),
                'iv': np.random.uniform(15, 25, 5)
            })
        
        except Exception as e:
            logger.error(f"Error fetching options chain: {e}")
            return None
    
    async def fetch_tick_data(self, symbol: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Fetch high-frequency tick data."""
        try:
            # Placeholder for tick data
            # In production: real-time WebSocket from broker
            logger.info(f"Fetching tick data for {symbol}")
            
            timestamps = pd.date_range(start=datetime.now() - timedelta(hours=1), 
                                      periods=limit, freq='1min')
            
            return pd.DataFrame({
                'timestamp': timestamps,
                'symbol': symbol,
                'bid': np.random.uniform(23800, 23900, limit),
                'ask': np.random.uniform(23800, 23900, limit),
                'bid_size': np.random.randint(100, 1000, limit),
                'ask_size': np.random.randint(100, 1000, limit)
            })
        
        except Exception as e:
            logger.error(f"Error fetching tick data: {e}")
            return None
    
    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price."""
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        return (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    
    async def aggregate_daily_data(self, symbols: List[str], 
                                  start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Aggregate daily OHLCV data for multiple symbols."""
        tasks = [
            self.fetch_market_data(symbol, period="max", interval="1d")
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks)
        
        data_dict = {}
        for symbol, df in zip(symbols, results):
            if df is not None:
                data_dict[symbol] = df
        
        return data_dict
    
    async def aggregate_intraday_data(self, symbols: List[str], 
                                     interval: str = "15m") -> Dict[str, pd.DataFrame]:
        """Aggregate intraday data for multiple symbols."""
        tasks = [
            self.fetch_market_data(symbol, period="5d", interval=interval)
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks)
        
        data_dict = {}
        for symbol, df in zip(symbols, results):
            if df is not None:
                data_dict[symbol] = df
        
        return data_dict
    
    async def store_market_data(self, data: pd.DataFrame) -> bool:
        """Store aggregated data in ClickHouse."""
        if not self.ch:
            logger.warning("ClickHouse connector not available")
            return False
        
        try:
            for _, row in data.iterrows():
                market_data = {
                    'timestamp': row['timestamp'],
                    'symbol': row['symbol'],
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                    'vwap': float(row['vwap']),
                    'bid': float(row['Close']) * 0.9999,
                    'ask': float(row['Close']) * 1.0001
                }
                
                self.ch.insert_market_data(market_data)
            
            logger.info(f"Stored {len(data)} records in ClickHouse")
            return True
        
        except Exception as e:
            logger.error(f"Error storing data: {e}")
            return False
    
    async def backfill_historical_data(self, symbols: List[str], 
                                      years: int = 5) -> Dict[str, Any]:
        """Backfill historical data for backtesting."""
        stats = {
            'symbols_processed': 0,
            'total_records': 0,
            'start_date': datetime.now() - timedelta(days=365*years),
            'end_date': datetime.now()
        }
        
        logger.info(f"Backfilling data for {len(symbols)} symbols over {years} years")
        
        daily_data = await self.aggregate_daily_data(symbols, 
                                                     str(stats['start_date']),
                                                     str(stats['end_date']))
        
        for symbol, df in daily_data.items():
            if df is not None:
                await self.store_market_data(df)
                stats['symbols_processed'] += 1
                stats['total_records'] += len(df)
        
        logger.info(f"Backfill complete: {stats['symbols_processed']} symbols, "
                   f"{stats['total_records']} records")
        
        return stats
    
    async def continuous_data_sync(self, symbols: List[str], 
                                  interval_minutes: int = 15):
        """Continuously sync data at regular intervals."""
        logger.info(f"Starting continuous data sync for {len(symbols)} symbols")
        
        while True:
            try:
                data = await self.aggregate_intraday_data(symbols, interval="15m")
                
                for symbol, df in data.items():
                    if df is not None:
                        await self.store_market_data(df)
                
                logger.info(f"Data sync complete at {datetime.now()}")
                
            except Exception as e:
                logger.error(f"Error in continuous sync: {e}")
            
            # Wait for next interval
            await asyncio.sleep(interval_minutes * 60)

class DataQualityMonitor:
    """Monitor data quality and consistency."""
    
    def __init__(self, clickhouse_connector=None):
        self.ch = clickhouse_connector
    
    def check_gaps(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        """Check for data gaps."""
        if not self.ch:
            return {}
        
        try:
            query = f"""
            SELECT 
                symbol,
                COUNT(*) as record_count,
                MAX(timestamp) as latest_timestamp,
                MIN(timestamp) as earliest_timestamp,
                DATEDIFF('day', MIN(timestamp), MAX(timestamp)) as days_covered
            FROM market_data
            WHERE symbol = '{symbol}' AND date >= today() - {days}
            GROUP BY symbol
            """
            
            result = self.ch.connection.execute(query)
            if result:
                row = result[0]
                return {
                    'symbol': row[0],
                    'records': row[1],
                    'latest': row[2],
                    'earliest': row[3],
                    'days_covered': row[4]
                }
        except Exception as e:
            logger.error(f"Error checking data gaps: {e}")
        
        return {}
    
    def check_data_integrity(self, symbol: str) -> Dict[str, Any]:
        """Check for data integrity issues."""
        issues = {
            'null_values': 0,
            'negative_volumes': 0,
            'invalid_prices': 0,
            'duplicate_records': 0
        }
        
        if not self.ch:
            return issues
        
        try:
            # Check for nulls
            query = f"SELECT COUNT(*) FROM market_data WHERE symbol = '{symbol}' AND close IS NULL"
            result = self.ch.connection.execute(query)
            issues['null_values'] = result[0][0] if result else 0
            
            # Check for negative volumes
            query = f"SELECT COUNT(*) FROM market_data WHERE symbol = '{symbol}' AND volume < 0"
            result = self.ch.connection.execute(query)
            issues['negative_volumes'] = result[0][0] if result else 0
            
            # Check for invalid prices (close < low or close > high)
            query = f"SELECT COUNT(*) FROM market_data WHERE symbol = '{symbol}' AND (close < low OR close > high)"
            result = self.ch.connection.execute(query)
            issues['invalid_prices'] = result[0][0] if result else 0
        
        except Exception as e:
            logger.error(f"Error checking integrity: {e}")
        
        return issues

# Example usage
async def example_usage():
    """Example data aggregation workflow."""
    # Initialize aggregator
    aggregator = DataAggregator()
    
    # Fetch NIFTY50 constituents data
    symbols = ['RELIANCE', 'TCS', 'INFY', 'WIPRO', 'HDFC']
    
    print("📊 Fetching intraday data...")
    intraday_data = await aggregator.aggregate_intraday_data(symbols, interval="15m")
    
    for symbol, df in intraday_data.items():
        print(f"✅ {symbol}: {len(df)} records")
    
    print("\n📈 Data aggregation complete!")
    
    # Quality check
    monitor = DataQualityMonitor()
    print("\n🔍 Data Quality Check:")
    print("✅ Gaps check implemented")
    print("✅ Integrity check implemented")

if __name__ == "__main__":
    asyncio.run(example_usage())
