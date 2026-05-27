"""
Technical Indicators - Industry-standard calculations.
RSI, MACD, Bollinger Bands, Volume Profile, SMA, EMA.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


def calculate_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index."""
    if len(closes) < period:
        return pd.Series([np.nan] * len(closes))
    
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(
    closes: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD and Signal line."""
    ema_fast = closes.ewm(span=fast).mean()
    ema_slow = closes.ewm(span=slow).mean()
    
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal).mean()
    histogram = macd - signal_line
    
    return macd, signal_line, histogram


def calculate_bollinger_bands(
    closes: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands."""
    sma = closes.rolling(window=period).mean()
    std = closes.rolling(window=period).std()
    
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return upper_band, sma, lower_band


def calculate_sma(closes: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return closes.rolling(window=period).mean()


def calculate_ema(closes: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return closes.ewm(span=period).mean()


def calculate_atr(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    period: int = 14
) -> pd.Series:
    """Calculate Average True Range."""
    tr1 = highs - lows
    tr2 = abs(highs - closes.shift())
    tr3 = abs(lows - closes.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def calculate_adx(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    period: int = 14
) -> pd.Series:
    """Calculate Average Directional Index (trend strength)."""
    # Directional movements
    plus_dm = highs.diff().clip(lower=0)
    minus_dm = (-lows.diff()).clip(lower=0)
    
    # Remove if both > 0
    for i in range(len(plus_dm)):
        if plus_dm.iloc[i] > minus_dm.iloc[i]:
            minus_dm.iloc[i] = 0
        elif minus_dm.iloc[i] > plus_dm.iloc[i]:
            plus_dm.iloc[i] = 0
    
    # True range
    tr1 = highs - lows
    tr2 = abs(highs - closes.shift())
    tr3 = abs(lows - closes.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Smoothed values
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1e-10)
    adx = dx.rolling(window=period).mean()
    
    return adx


def calculate_volume_ratio(volumes: pd.Series, period: int = 20) -> pd.Series:
    """Calculate volume strength (current vol / average vol)."""
    avg_vol = volumes.rolling(window=period).mean()
    vol_ratio = volumes / avg_vol.replace(0, 1e-10)
    return vol_ratio


class TechnicalAnalyzer:
    """High-level technical analysis with multi-indicator scoring."""
    
    @staticmethod
    def analyze_stock(df: pd.DataFrame, symbol: str = "") -> Dict:
        """
        Complete technical analysis of a stock.
        Requires OHLCV DataFrame with columns: Open, High, Low, Close, Volume.
        
        Returns: {
            'symbol': str,
            'price': float,
            'rsi': float,
            'macd_hist': float,
            'bb_position': float (0-1),
            'atr_pct': float,
            'adx': float,
            'volume_ratio': float,
            'trend': str ('UP', 'DOWN', 'NEUTRAL'),
            'momentum_score': float (0-100),
        }
        """
        if df.empty or len(df) < 50:
            return {}
        
        # Extract OHLCV
        closes = df['Close']
        highs = df['High']
        lows = df['Low']
        volumes = df['Volume']
        
        # Calculate indicators
        rsi = calculate_rsi(closes, 14).iloc[-1]
        macd, signal, hist = calculate_macd(closes, 12, 26, 9)
        macd_hist = hist.iloc[-1]
        
        bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(closes, 20, 2.0)
        current_price = closes.iloc[-1]
        bb_range = bb_upper.iloc[-1] - bb_lower.iloc[-1]
        bb_position = ((current_price - bb_lower.iloc[-1]) / bb_range) if bb_range > 0 else 0.5
        
        atr = calculate_atr(highs, lows, closes, 14).iloc[-1]
        atr_pct = (atr / current_price * 100) if current_price > 0 else 0
        
        adx = calculate_adx(highs, lows, closes, 14).iloc[-1]
        vol_ratio = calculate_volume_ratio(volumes, 20).iloc[-1]
        
        # SMAs for trend
        sma_20 = calculate_sma(closes, 20).iloc[-1]
        sma_50 = calculate_sma(closes, 50).iloc[-1]
        sma_200 = calculate_sma(closes, 200).iloc[-1] if len(df) >= 200 else sma_50
        
        # Determine trend
        if current_price > sma_20 > sma_50 > sma_200:
            trend = "UP"
        elif current_price < sma_20 < sma_50 < sma_200:
            trend = "DOWN"
        else:
            trend = "NEUTRAL"
        
        # Momentum score (0-100)
        momentum_score = 0
        
        # RSI contribution (30%)
        if rsi < 30:
            momentum_score += 30  # Oversold
        elif rsi > 70:
            momentum_score -= 10  # Overbought
        else:
            momentum_score += (50 - rsi) * 0.3  # Mid-range bias
        
        # MACD contribution (20%)
        if macd_hist > 0:
            momentum_score += 20
        elif macd_hist < -5:
            momentum_score -= 10
        
        # Bollinger contribution (20%)
        if bb_position > 0.8:
            momentum_score += 10  # Near upper
        elif bb_position < 0.2:
            momentum_score += 20  # Near lower (oversold)
        
        # Trend contribution (20%)
        if trend == "UP":
            momentum_score += 20
        elif trend == "DOWN":
            momentum_score -= 10
        
        # ADX contribution (10%)
        if adx > 25:
            momentum_score += 10  # Strong trend
        elif adx < 15:
            momentum_score -= 5   # Weak trend
        
        momentum_score = max(0, min(100, momentum_score))  # Clamp 0-100
        
        return {
            "symbol": symbol,
            "price": round(current_price, 2),
            "rsi": round(rsi, 2),
            "macd_hist": round(macd_hist, 4),
            "bb_position": round(bb_position, 3),
            "atr_pct": round(atr_pct, 2),
            "adx": round(adx, 2),
            "volume_ratio": round(vol_ratio, 2),
            "trend": trend,
            "momentum_score": round(momentum_score, 1),
            "sma_20": round(sma_20, 2),
            "sma_50": round(sma_50, 2),
            "sma_200": round(sma_200, 2),
        }
