"""Historical Data Engine - Fetch, store, and query historical market data."""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class HistoricalDataEngine:
    """Manage historical data for backtesting and analysis."""
    
    def __init__(self, clickhouse_connector=None):
        self.ch = clickhouse_connector
        self.cache = {}
        self.executor = ThreadPoolExecutor(max_workers=20)
        
        # Common stock universes
        self.NIFTY50 = ['RELIANCE', 'TCS', 'INFY', 'WIPRO', 'HDFC', 'HSBC', 
                        'LT', 'BAJAJ-AUTO', 'MARUTI', 'SUNPHARMA', 'ITC', 'LTIM',
                        'JSWSTEEL', 'COALINDIA', 'BHARTIARTL', 'TECHM', 'POWERGRID',
                        'ONGC', 'NTPC', 'SBIN', 'ICICIBANK', 'AXISBANK', 'INDIGO',
                        'GRASIM', 'BAJAJFINSV', 'M&M', 'EICHERMOT', 'APOLLOHOSP',
                        'DRREDDY', 'TITAN', 'HDFCBANK', 'ASIANPAINT', 'ULTRASONIC',
                        'DLF', 'ADANIENT', 'ADANIPORTS', 'ADANIPOWER', 'PIDILITIND']
    
    async def fetch_and_store_daily_data(self, symbols: List[str], 
                                        years: int = 5) -> Dict[str, int]:
        """Fetch and store daily OHLCV data."""
        results = {}
        start_date = datetime.now() - timedelta(days=365*years)
        
        logger.info(f"Fetching {len(symbols)} symbols, {years} years of daily data")
        
        for symbol in symbols:
            try:
                ticker = f"{symbol}.NS"
                df = yf.download(ticker, start=start_date, progress=False)
                
                if df.empty:
                    logger.warning(f"No data for {symbol}")
                    results[symbol] = 0
                    continue
                
                # Prepare data for storage
                records_stored = 0
                
                if self.ch:
                    for idx, row in df.iterrows():
                        market_data = {
                            'timestamp': idx,
                            'symbol': symbol,
                            'open': float(row['Open']),
                            'high': float(row['High']),
                            'low': float(row['Low']),
                            'close': float(row['Close']),
                            'volume': int(row['Volume']),
                            'vwap': float(row['Close']),  # Simplified
                            'bid': float(row['Close']) * 0.9999,
                            'ask': float(row['Close']) * 1.0001
                        }
                        
                        if self.ch.insert_market_data(market_data):
                            records_stored += 1
                
                results[symbol] = records_stored
                logger.info(f"✅ {symbol}: {records_stored} daily records")
            
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                results[symbol] = 0
        
        return results
    
    async def fetch_and_store_intraday_data(self, symbols: List[str], 
                                           interval: str = "15m",
                                           days: int = 30) -> Dict[str, int]:
        """Fetch and store intraday data."""
        results = {}
        start_date = datetime.now() - timedelta(days=days)
        
        logger.info(f"Fetching {len(symbols)} symbols, intraday {interval} data")
        
        tasks = []
        for symbol in symbols:
            tasks.append(self._fetch_intraday_symbol(symbol, interval, start_date))
        
        results = await asyncio.gather(*tasks)
        return dict(zip(symbols, results))
    
    async def _fetch_intraday_symbol(self, symbol: str, interval: str, 
                                    start_date: datetime) -> int:
        """Fetch intraday data for single symbol."""
        try:
            ticker = f"{symbol}.NS"
            df = yf.download(ticker, start=start_date, interval=interval, 
                           progress=False, threads=False)
            
            if df.empty:
                return 0
            
            records_stored = 0
            if self.ch:
                for idx, row in df.iterrows():
                    market_data = {
                        'timestamp': idx,
                        'symbol': symbol,
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close']),
                        'volume': int(row['Volume']),
                        'vwap': float(row['Close']),
                        'bid': float(row['Close']) * 0.9999,
                        'ask': float(row['Close']) * 1.0001
                    }
                    
                    if self.ch.insert_market_data(market_data):
                        records_stored += 1
            
            logger.info(f"✅ {symbol}: {records_stored} {interval} records")
            return records_stored
        
        except Exception as e:
            logger.error(f"Error fetching {symbol} intraday: {e}")
            return 0
    
    def get_historical_data(self, symbol: str, start_date: str, 
                           end_date: str) -> Optional[pd.DataFrame]:
        """Get historical data from ClickHouse."""
        if not self.ch:
            logger.warning("ClickHouse not available")
            return None
        
        try:
            query = f"""
            SELECT timestamp, symbol, open, high, low, close, volume
            FROM market_data
            WHERE symbol = '{symbol}' 
            AND date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY timestamp ASC
            """
            
            result = self.ch.connection.execute(query)
            
            if not result:
                return None
            
            df = pd.DataFrame(result, columns=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        
        except Exception as e:
            logger.error(f"Error querying historical data: {e}")
            return None
    
    def get_ohlcv_range(self, symbol: str, days: int = 252) -> Optional[pd.DataFrame]:
        """Get OHLCV data for last N days."""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        return self.get_historical_data(symbol, start_date, end_date)
    
    async def calculate_returns(self, symbol: str, days: int = 252) -> Dict[str, float]:
        """Calculate returns metrics."""
        df = self.get_ohlcv_range(symbol, days)
        
        if df is None or df.empty:
            return {}
        
        df['returns'] = df['close'].pct_change()
        
        return {
            'daily_return': float(df['returns'].mean()),
            'annual_return': float(df['returns'].mean() * 252),
            'volatility': float(df['returns'].std() * np.sqrt(252)),
            'cumulative_return': float((df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100),
            'sharpe_ratio': float((df['returns'].mean() * 252) / (df['returns'].std() * np.sqrt(252)))
        }
    
    async def backfill_universe(self, universe: List[str], years: int = 5) -> Dict[str, Any]:
        """Backfill complete universe."""
        logger.info(f"Backfilling {len(universe)} symbols, {years} years")
        
        start_time = datetime.now()
        
        # Fetch and store daily data
        daily_results = await self.fetch_and_store_daily_data(universe, years)
        
        total_records = sum(daily_results.values())
        successful = sum(1 for v in daily_results.values() if v > 0)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            'symbols_requested': len(universe),
            'symbols_successful': successful,
            'total_records_stored': total_records,
            'duration_seconds': duration,
            'records_per_second': total_records / duration if duration > 0 else 0,
            'timestamp': datetime.now().isoformat()
        }
    
    async def continuous_daily_update(self):
        """Continuously update daily data."""
        logger.info("Starting continuous daily update")
        
        while True:
            try:
                # Update NIFTY50 daily
                results = await self.fetch_and_store_daily_data(self.NIFTY50, years=1)
                
                successful = sum(1 for v in results.values() if v > 0)
                total = sum(results.values())
                
                logger.info(f"Daily update: {successful} symbols, {total} records at {datetime.now()}")
            
            except Exception as e:
                logger.error(f"Error in daily update: {e}")
            
            # Run at 4:00 AM daily
            next_run = datetime.now().replace(hour=4, minute=0, second=0)
            if next_run <= datetime.now():
                next_run += timedelta(days=1)
            
            wait_seconds = (next_run - datetime.now()).total_seconds()
            await asyncio.sleep(wait_seconds)

class DataCache:
    """In-memory cache for frequently accessed data."""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache = {}
        self.ttl = ttl_minutes * 60  # Convert to seconds
        self.access_times = {}
    
    def get(self, key: str) -> Optional[pd.DataFrame]:
        """Get data from cache."""
        if key not in self.cache:
            return None
        
        # Check TTL
        if datetime.now().timestamp() - self.access_times[key] > self.ttl:
            del self.cache[key]
            del self.access_times[key]
            return None
        
        return self.cache[key]
    
    def set(self, key: str, data: pd.DataFrame) -> None:
        """Store data in cache."""
        self.cache[key] = data
        self.access_times[key] = datetime.now().timestamp()
    
    def clear(self) -> None:
        """Clear entire cache."""
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cached_symbols': len(self.cache),
            'cache_size_mb': sum(sys.getsizeof(v) for v in self.cache.values()) / (1024 * 1024),
            'ttl_minutes': self.ttl // 60
        }

# Required imports
import sys
import numpy as np

# Example usage
async def example_backfill():
    """Example backfill workflow."""
    engine = HistoricalDataEngine()
    
    # Backfill NIFTY50 for 1 year
    results = await engine.backfill_universe(engine.NIFTY50[:5], years=1)
    
    print("\n📊 Backfill Results:")
    print(f"✅ Symbols: {results['symbols_successful']}/{results['symbols_requested']}")
    print(f"✅ Total Records: {results['total_records_stored']}")
    print(f"✅ Duration: {results['duration_seconds']:.1f} seconds")
    print(f"✅ Throughput: {results['records_per_second']:.0f} records/second")

if __name__ == "__main__":
    asyncio.run(example_backfill())
