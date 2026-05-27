"""Greeks Sensitivity Analysis - Interactive heatmaps and sensitivity tables."""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class GreeksSensitivity:
    """Greeks sensitivity metrics."""
    base_value: float  # Current option value
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    
    # Sensitivity ranges
    delta_change: float  # Change per 1% move in underlying
    vega_change: float   # Change per 1% IV increase
    theta_change: float  # Change per 1 day
    gamma_change: float  # Change in delta per 1% move

class GreeksSensitivityCalculator:
    """Calculate Greeks sensitivity to price, IV, and time."""
    
    def __init__(self):
        try:
            from scipy.stats import norm
            from scipy.optimize import minimize_scalar
            self.norm = norm
            self.minimize_scalar = minimize_scalar
            self.available = True
        except ImportError:
            logger.warning("scipy not installed. Install: pip install scipy")
            self.available = False
    
    def generate_price_sensitivity(self, current_price: float, 
                                 strike: float, expiry_days: int,
                                 option_type: str = "CALL",
                                 iv: float = 0.20) -> pd.DataFrame:
        """Generate Greeks sensitivity to price changes."""
        
        price_range = np.linspace(
            current_price * 0.85,
            current_price * 1.15,
            21
        )
        
        sensitivities = []
        
        for price in price_range:
            # Simplified Greeks calculation (for production: use Black-Scholes)
            intrinsic = max(price - strike, 0) if option_type == "CALL" else max(strike - price, 0)
            
            moneyness = price / strike
            days_to_expiry = max(expiry_days, 0.01)
            
            # Approximated Greeks
            delta = self._approx_delta(moneyness, option_type)
            gamma = self._approx_gamma(moneyness, iv, days_to_expiry)
            theta = self._approx_theta(intrinsic, iv, days_to_expiry)
            vega = self._approx_vega(moneyness, days_to_expiry)
            
            option_value = intrinsic + (iv * price * days_to_expiry ** 0.5) * 0.4
            
            sensitivities.append({
                'price': price,
                'price_change_%': (price - current_price) / current_price * 100,
                'option_value': option_value,
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega,
                'iv': iv
            })
        
        return pd.DataFrame(sensitivities)
    
    def generate_iv_sensitivity(self, current_price: float,
                               strike: float, expiry_days: int,
                               option_type: str = "CALL") -> pd.DataFrame:
        """Generate Greeks sensitivity to IV changes."""
        
        iv_range = np.linspace(0.10, 0.60, 11)
        
        sensitivities = []
        
        for iv in iv_range:
            intrinsic = max(current_price - strike, 0) if option_type == "CALL" else max(strike - current_price, 0)
            
            moneyness = current_price / strike
            days_to_expiry = max(expiry_days, 0.01)
            
            # Greeks
            delta = self._approx_delta(moneyness, option_type)
            gamma = self._approx_gamma(moneyness, iv, days_to_expiry)
            theta = self._approx_theta(intrinsic, iv, days_to_expiry)
            vega = self._approx_vega(moneyness, days_to_expiry)
            
            option_value = intrinsic + (iv * current_price * days_to_expiry ** 0.5) * 0.4
            
            sensitivities.append({
                'iv': iv,
                'iv_%': iv * 100,
                'option_value': option_value,
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega
            })
        
        return pd.DataFrame(sensitivities)
    
    def generate_time_sensitivity(self, current_price: float,
                                 strike: float, max_days: int = 90,
                                 option_type: str = "CALL",
                                 iv: float = 0.20) -> pd.DataFrame:
        """Generate Greeks sensitivity to time decay."""
        
        days_range = np.linspace(max_days, 1, 30)
        
        sensitivities = []
        
        for days in days_range:
            intrinsic = max(current_price - strike, 0) if option_type == "CALL" else max(strike - current_price, 0)
            
            moneyness = current_price / strike
            days_to_expiry = max(days, 0.01)
            
            # Greeks
            delta = self._approx_delta(moneyness, option_type)
            gamma = self._approx_gamma(moneyness, iv, days_to_expiry)
            theta = self._approx_theta(intrinsic, iv, days_to_expiry)
            vega = self._approx_vega(moneyness, days_to_expiry)
            
            option_value = intrinsic + (iv * current_price * days_to_expiry ** 0.5) * 0.4
            
            sensitivities.append({
                'days_to_expiry': days,
                'option_value': option_value,
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega
            })
        
        return pd.DataFrame(sensitivities)
    
    def generate_2d_greeks_heatmap(self, current_price: float,
                                  strike: float, expiry_days: int,
                                  greek: str = "delta",
                                  option_type: str = "CALL") -> pd.DataFrame:
        """Generate 2D heatmap of Greeks across price and IV."""
        
        prices = np.linspace(current_price * 0.9, current_price * 1.1, 15)
        ivs = np.linspace(0.10, 0.50, 15)
        
        heatmap = np.zeros((len(ivs), len(prices)))
        
        for i, iv in enumerate(ivs):
            for j, price in enumerate(prices):
                intrinsic = max(price - strike, 0) if option_type == "CALL" else max(strike - price, 0)
                moneyness = price / strike
                days_to_expiry = max(expiry_days, 0.01)
                
                if greek == "delta":
                    value = self._approx_delta(moneyness, option_type)
                elif greek == "gamma":
                    value = self._approx_gamma(moneyness, iv, days_to_expiry)
                elif greek == "theta":
                    value = self._approx_theta(intrinsic, iv, days_to_expiry)
                elif greek == "vega":
                    value = self._approx_vega(moneyness, days_to_expiry)
                else:
                    value = 0
                
                heatmap[i, j] = value
        
        return pd.DataFrame(heatmap, index=ivs, columns=prices)
    
    @staticmethod
    def _approx_delta(moneyness: float, option_type: str = "CALL") -> float:
        """Approximate delta."""
        delta = np.tanh((moneyness - 1) * 2)
        if option_type == "CALL":
            return 0.5 + delta * 0.5
        else:
            return 0.5 - delta * 0.5
    
    @staticmethod
    def _approx_gamma(moneyness: float, iv: float, days_to_expiry: float) -> float:
        """Approximate gamma."""
        return np.exp(-(moneyness - 1) ** 2 / (2 * (iv ** 2))) / (iv * days_to_expiry ** 0.5)
    
    @staticmethod
    def _approx_theta(intrinsic: float, iv: float, days_to_expiry: float) -> float:
        """Approximate theta (daily decay)."""
        extrinsic = max(iv * 10 * days_to_expiry ** 0.5 - intrinsic, 0)
        return -extrinsic / max(days_to_expiry, 1)
    
    @staticmethod
    def _approx_vega(moneyness: float, days_to_expiry: float) -> float:
        """Approximate vega (per 1% IV change)."""
        return days_to_expiry ** 0.5 * np.exp(-(moneyness - 1) ** 2 / 2)

class PortfolioGreeksSensitivity:
    """Analyze Greeks sensitivity for entire portfolio."""
    
    def __init__(self):
        self.calculator = GreeksSensitivityCalculator()
    
    def portfolio_sensitivity_summary(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate portfolio-level Greeks sensitivity summary."""
        
        total_delta = sum(p.get('delta', 0) for p in positions)
        total_gamma = sum(p.get('gamma', 0) for p in positions)
        total_theta = sum(p.get('theta', 0) for p in positions)
        total_vega = sum(p.get('vega', 0) for p in positions)
        
        # Sensitivity to 1% market move
        delta_exposure = total_delta * 100  # P&L impact
        gamma_exposure = total_gamma * 100 * 100  # Delta change impact
        
        return {
            'total_delta': total_delta,
            'total_gamma': total_gamma,
            'total_theta': total_theta,
            'total_vega': total_vega,
            'delta_exposure': delta_exposure,
            'gamma_exposure': gamma_exposure,
            'positions_count': len(positions)
        }
    
    def scenario_analysis(self, positions: List[Dict[str, Any]],
                         price_moves: List[float],
                         iv_moves: List[float]) -> pd.DataFrame:
        """Analyze portfolio P&L under different scenarios."""
        
        scenarios = []
        
        for price_move in price_moves:
            for iv_move in iv_moves:
                pnl = 0
                
                for pos in positions:
                    # Simple P&L estimation
                    delta_pnl = pos.get('delta', 0) * price_move * pos.get('notional', 1000)
                    vega_pnl = pos.get('vega', 0) * iv_move * 100  # IV move in bps
                    theta_pnl = pos.get('theta', 0) * 1  # 1 day theta
                    
                    pnl += delta_pnl + vega_pnl + theta_pnl
                
                scenarios.append({
                    'price_move_%': price_move * 100,
                    'iv_move_bps': iv_move * 10000,
                    'portfolio_pnl': pnl
                })
        
        return pd.DataFrame(scenarios)

# Example usage
def example_greeks_sensitivity():
    """Example Greeks sensitivity analysis."""
    
    calculator = GreeksSensitivityCalculator()
    
    print("📊 Price Sensitivity:")
    price_sens = calculator.generate_price_sensitivity(
        current_price=23894,
        strike=23900,
        expiry_days=30,
        option_type="CALL",
        iv=0.20
    )
    print(price_sens[['price', 'price_change_%', 'delta', 'gamma', 'theta', 'vega']].to_string())
    
    print("\n📈 IV Sensitivity:")
    iv_sens = calculator.generate_iv_sensitivity(
        current_price=23894,
        strike=23900,
        expiry_days=30,
        option_type="CALL"
    )
    print(iv_sens[['iv_%', 'delta', 'gamma', 'theta', 'vega']].to_string())
    
    print("\n⏰ Time Sensitivity:")
    time_sens = calculator.generate_time_sensitivity(
        current_price=23894,
        strike=23900,
        max_days=60,
        option_type="CALL"
    )
    print(time_sens[['days_to_expiry', 'delta', 'gamma', 'theta', 'vega']].to_string())
    
    print("\n✅ Greeks sensitivity analysis complete!")

if __name__ == "__main__":
    example_greeks_sensitivity()
