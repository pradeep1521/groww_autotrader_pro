"""Options Greeks Calculator - Delta, Gamma, Theta, Vega, Rho."""

import numpy as np
from scipy.stats import norm
from dataclasses import dataclass
from typing import Dict, Tuple
from datetime import datetime, timedelta

@dataclass
class Greeks:
    """Options Greeks."""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float

class BlackScholesCalculator:
    """Black-Scholes options pricing and Greeks calculation."""
    
    @staticmethod
    def d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d1 parameter."""
        if T <= 0:
            return 0
        numerator = np.log(S / K) + (r + 0.5 * sigma ** 2) * T
        denominator = sigma * np.sqrt(T)
        return numerator / denominator
    
    @staticmethod
    def d2(d1: float, sigma: float, T: float) -> float:
        """Calculate d2 parameter."""
        if T <= 0:
            return d1
        return d1 - sigma * np.sqrt(T)
    
    @staticmethod
    def call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate call option price using Black-Scholes."""
        if T <= 0:
            return max(S - K, 0)
        
        d1 = BlackScholesCalculator.d1(S, K, T, r, sigma)
        d2 = BlackScholesCalculator.d2(d1, sigma, T)
        
        call = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        return max(call, 0)
    
    @staticmethod
    def put_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate put option price using Black-Scholes."""
        if T <= 0:
            return max(K - S, 0)
        
        d1 = BlackScholesCalculator.d1(S, K, T, r, sigma)
        d2 = BlackScholesCalculator.d2(d1, sigma, T)
        
        put = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        return max(put, 0)
    
    @staticmethod
    def call_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate call delta."""
        if T <= 0:
            return 1.0 if S > K else 0.0
        
        d1 = BlackScholesCalculator.d1(S, K, T, r, sigma)
        return norm.cdf(d1)
    
    @staticmethod
    def put_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate put delta."""
        if T <= 0:
            return -1.0 if S < K else 0.0
        
        d1 = BlackScholesCalculator.d1(S, K, T, r, sigma)
        return norm.cdf(d1) - 1
    
    @staticmethod
    def gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate gamma (same for calls and puts)."""
        if T <= 0 or sigma == 0:
            return 0
        
        d1 = BlackScholesCalculator.d1(S, K, T, r, sigma)
        return norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    @staticmethod
    def call_theta(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate call theta (per day)."""
        if T <= 0:
            return 0
        
        d1 = BlackScholesCalculator.d1(S, K, T, r, sigma)
        d2 = BlackScholesCalculator.d2(d1, sigma, T)
        
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 
                 r * K * np.exp(-r * T) * norm.cdf(d2))
        
        return theta / 365  # Convert to per day
    
    @staticmethod
    def put_theta(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate put theta (per day)."""
        if T <= 0:
            return 0
        
        d1 = BlackScholesCalculator.d1(S, K, T, r, sigma)
        d2 = BlackScholesCalculator.d2(d1, sigma, T)
        
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + 
                 r * K * np.exp(-r * T) * norm.cdf(-d2))
        
        return theta / 365  # Convert to per day
    
    @staticmethod
    def vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate vega (per 1% change in volatility)."""
        if T <= 0 or sigma == 0:
            return 0
        
        d1 = BlackScholesCalculator.d1(S, K, T, r, sigma)
        return S * norm.pdf(d1) * np.sqrt(T) / 100  # Per 1% volatility change
    
    @staticmethod
    def rho(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
        """Calculate rho (per 1% change in interest rate)."""
        if T <= 0:
            return 0
        
        d2 = BlackScholesCalculator.d2(
            BlackScholesCalculator.d1(S, K, T, r, sigma), sigma, T
        )
        
        if option_type.lower() == 'call':
            return K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:  # put
            return -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100

class OptionsChainCalculator:
    """Calculate Greeks for complete option chain."""
    
    def __init__(self, spot_price: float, risk_free_rate: float = 0.06, 
                 volatility: float = 0.20):
        self.spot = spot_price
        self.rate = risk_free_rate
        self.vol = volatility
    
    def calculate_chain(self, strikes: list, expiry_days: int, 
                       option_type: str = 'call') -> Dict[float, Greeks]:
        """Calculate Greeks for all strikes."""
        T = expiry_days / 365.0
        results = {}
        
        for strike in strikes:
            if option_type.lower() == 'call':
                delta = BlackScholesCalculator.call_delta(self.spot, strike, T, self.rate, self.vol)
                theta = BlackScholesCalculator.call_theta(self.spot, strike, T, self.rate, self.vol)
                price = BlackScholesCalculator.call_price(self.spot, strike, T, self.rate, self.vol)
            else:
                delta = BlackScholesCalculator.put_delta(self.spot, strike, T, self.rate, self.vol)
                theta = BlackScholesCalculator.put_theta(self.spot, strike, T, self.rate, self.vol)
                price = BlackScholesCalculator.put_price(self.spot, strike, T, self.rate, self.vol)
            
            gamma = BlackScholesCalculator.gamma(self.spot, strike, T, self.rate, self.vol)
            vega = BlackScholesCalculator.vega(self.spot, strike, T, self.rate, self.vol)
            rho = BlackScholesCalculator.rho(self.spot, strike, T, self.rate, self.vol, option_type)
            
            results[strike] = {
                'price': round(price, 2),
                'delta': round(delta, 4),
                'gamma': round(gamma, 6),
                'theta': round(theta, 4),
                'vega': round(vega, 2),
                'rho': round(rho, 4)
            }
        
        return results
    
    def calculate_iv(self, market_price: float, strike: float, expiry_days: int, 
                    option_type: str = 'call') -> float:
        """Calculate implied volatility using binary search."""
        T = expiry_days / 365.0
        vol_min, vol_max = 0.001, 3.0
        
        for _ in range(50):  # Iterations
            vol_mid = (vol_min + vol_max) / 2
            
            if option_type.lower() == 'call':
                price = BlackScholesCalculator.call_price(self.spot, strike, T, self.rate, vol_mid)
            else:
                price = BlackScholesCalculator.put_price(self.spot, strike, T, self.rate, vol_mid)
            
            if price < market_price:
                vol_min = vol_mid
            else:
                vol_max = vol_mid
        
        return round(vol_mid, 4)

def generate_option_chain(spot: float, expiry_days: int = 7) -> Dict:
    """Generate complete option chain with Greeks."""
    calculator = OptionsChainCalculator(spot)
    
    # Generate strikes around ATM
    atm_strike = int(spot / 100) * 100
    strikes = [atm_strike + (i * 100) for i in range(-5, 6)]
    
    calls = calculator.calculate_chain(strikes, expiry_days, 'call')
    puts = calculator.calculate_chain(strikes, expiry_days, 'put')
    
    chain = {
        'spot': spot,
        'expiry_days': expiry_days,
        'strikes': strikes,
        'calls': calls,
        'puts': puts
    }
    
    return chain

# Example usage
if __name__ == "__main__":
    # Generate option chain for NIFTY50 (spot = 23894.10)
    chain = generate_option_chain(spot=23894.10, expiry_days=7)
    
    print("📊 Option Chain - NIFTY50 (7 DTE)")
    print(f"Spot: {chain['spot']}")
    print("\nCall Greeks (sample strikes):")
    for strike in [23800, 23900, 24000]:
        call_greeks = chain['calls'][strike]
        print(f"  Strike {strike}: Delta={call_greeks['delta']}, "
              f"Theta={call_greeks['theta']}, Vega={call_greeks['vega']}")
    
    print("\nPut Greeks (sample strikes):")
    for strike in [23800, 23900, 24000]:
        put_greeks = chain['puts'][strike]
        print(f"  Strike {strike}: Delta={put_greeks['delta']}, "
              f"Theta={put_greeks['theta']}, Vega={put_greeks['vega']}")
