"""Data caching layer to prevent yfinance rate limits."""

import os
import json
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

CACHE_DIR = Path("./data/cache")
CACHE_DURATION = timedelta(hours=1)  # Cache valid for 1 hour

def _get_cache_file(symbol: str, period: str) -> Path:
    """Get cache file path for symbol."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_symbol = symbol.replace(".", "_").replace(" ", "_")
    return CACHE_DIR / f"{safe_symbol}_{period}.json"

def _is_cache_valid(cache_file: Path) -> bool:
    """Check if cache file exists and is still valid."""
    if not cache_file.exists():
        return False
    
    file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
    return file_age < CACHE_DURATION

def _save_cache(symbol: str, period: str, df: pd.DataFrame) -> None:
    """Save DataFrame to cache."""
    try:
        cache_file = _get_cache_file(symbol, period)
        
        # Convert DataFrame to JSON-serializable format
        cache_data = {
            "symbol": symbol,
            "period": period,
            "timestamp": datetime.now().isoformat(),
            "data": df.reset_index().to_dict('records')
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
    except Exception as e:
        print(f"⚠️ Cache save failed: {e}")

def _load_cache(symbol: str, period: str) -> pd.DataFrame:
    """Load DataFrame from cache."""
    try:
        cache_file = _get_cache_file(symbol, period)
        
        if not _is_cache_valid(cache_file):
            return None
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Reconstruct DataFrame
        df = pd.DataFrame(cache_data['data'])
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        return df
    except Exception as e:
        print(f"⚠️ Cache load failed: {e}")
        return None

def download_stock_data(symbol: str, period: str = "3mo", use_cache: bool = True) -> pd.DataFrame:
    """
    Download stock data with caching.
    
    Args:
        symbol: Stock symbol (e.g., "RELIANCE.NS")
        period: Period (1d, 5d, 3mo, etc.)
        use_cache: Use cached data if available
    
    Returns:
        DataFrame with OHLCV data, or empty DataFrame on failure
    """
    # Try cache first
    if use_cache:
        cached_df = _load_cache(symbol, period)
        if cached_df is not None and not cached_df.empty:
            print(f"✅ Using cached data for {symbol}")
            return cached_df
    
    # Download fresh data
    try:
        print(f"📥 Downloading {symbol}...")
        df = yf.download(
            symbol,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False
        )
        
        if not df.empty:
            _save_cache(symbol, period, df)
            print(f"✅ Downloaded and cached {symbol}")
        
        return df
    
    except Exception as e:
        print(f"❌ Download failed for {symbol}: {e}")
        
        # Try to return stale cache as fallback
        cached_df = _load_cache(symbol, period)
        if cached_df is not None and not cached_df.empty:
            print(f"⚠️ Using stale cache for {symbol}")
            return cached_df
        
        return pd.DataFrame()

def clear_cache() -> None:
    """Clear all cache files."""
    try:
        import shutil
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        print("✅ Cache cleared")
    except Exception as e:
        print(f"❌ Cache clear failed: {e}")
