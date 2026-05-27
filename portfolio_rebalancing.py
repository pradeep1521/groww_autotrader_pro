"""Portfolio Rebalancing - Markowitz optimization and risk parity allocation."""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class PortfolioWeights:
    """Portfolio allocation weights."""
    allocations: Dict[str, float]  # symbol -> weight
    timestamp: datetime
    rebalance_reason: str = ""
    expected_return: float = 0
    expected_volatility: float = 0
    sharpe_ratio: float = 0

class CovarianceMatrix:
    """Calculate and cache covariance matrix."""
    
    def __init__(self, lookback_days: int = 252):
        self.lookback_days = lookback_days
        self.cached_cov = None
        self.cached_timestamp = None
    
    def calculate(self, returns: pd.DataFrame) -> np.ndarray:
        """Calculate annualized covariance matrix from returns."""
        
        # Use last lookback_days of data
        recent_returns = returns.tail(self.lookback_days)
        
        # Annualize (252 trading days)
        cov_matrix = recent_returns.cov() * 252
        
        self.cached_cov = cov_matrix
        self.cached_timestamp = datetime.now()
        
        return cov_matrix.values

class Markowitz:
    """Markowitz mean-variance portfolio optimization."""
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
    
    def optimal_portfolio(self, expected_returns: np.ndarray,
                         cov_matrix: np.ndarray,
                         constraints: Dict[str, Any] = None) -> Tuple[np.ndarray, float, float]:
        """
        Find optimal portfolio weights using Markowitz optimization.
        
        Args:
            expected_returns: Annual expected returns for each asset
            cov_matrix: Covariance matrix
            constraints: {min_weight, max_weight, sector_limits}
        
        Returns:
            weights: Optimal weights
            expected_return: Portfolio expected return
            expected_volatility: Portfolio expected volatility
        """
        
        n = len(expected_returns)
        constraints = constraints or {}
        
        min_weight = constraints.get('min_weight', 0)
        max_weight = constraints.get('max_weight', 1)
        
        # Simple optimization: maximize Sharpe ratio
        best_weights = None
        best_sharpe = -np.inf
        
        # Grid search over weights
        for _ in range(1000):
            # Generate random weights
            weights = np.random.dirichlet(np.ones(n))
            
            # Apply constraints
            weights = np.clip(weights, min_weight, max_weight)
            weights /= weights.sum()  # Renormalize
            
            # Calculate metrics
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_weights = weights
        
        portfolio_return = np.dot(best_weights, expected_returns)
        portfolio_vol = np.sqrt(np.dot(best_weights, np.dot(cov_matrix, best_weights)))
        
        return best_weights, portfolio_return, portfolio_vol
    
    def minimum_variance_portfolio(self, cov_matrix: np.ndarray) -> Tuple[np.ndarray, float]:
        """Find minimum variance portfolio."""
        
        n = cov_matrix.shape[0]
        
        # Minimize volatility
        inv_cov = np.linalg.inv(cov_matrix)
        ones = np.ones(n)
        
        weights = inv_cov @ ones
        weights /= weights.sum()
        
        volatility = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        
        return weights, volatility

class RiskParity:
    """Risk parity portfolio allocation."""
    
    @staticmethod
    def allocate(cov_matrix: np.ndarray, target_volatility: float = 0.12) -> np.ndarray:
        """
        Allocate weights so each asset contributes equal risk.
        
        Args:
            cov_matrix: Covariance matrix
            target_volatility: Target portfolio volatility
        
        Returns:
            weights: Risk parity weights
        """
        
        # Inverse volatility weighting (risk parity)
        inv_vol = 1 / np.sqrt(np.diag(cov_matrix))
        weights = inv_vol / inv_vol.sum()
        
        # Scale to target volatility
        portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        scaling_factor = target_volatility / portfolio_vol
        
        # This would require leveraging, so cap at 100% allocation
        weights = weights * min(scaling_factor, 1.0)
        weights /= weights.sum()
        
        return weights
    
    @staticmethod
    def equal_weight(n_assets: int) -> np.ndarray:
        """Equal weight allocation."""
        return np.ones(n_assets) / n_assets

class RebalanceStrategy:
    """Portfolio rebalancing strategies."""
    
    def __init__(self, portfolio: Dict[str, float], 
                 target_weights: Dict[str, float],
                 transaction_cost: float = 0.001):
        """
        Initialize rebalancing strategy.
        
        Args:
            portfolio: Current holdings {symbol: quantity}
            target_weights: Target allocation {symbol: weight}
            transaction_cost: Trading cost as % of trade value
        """
        
        self.portfolio = portfolio
        self.target_weights = target_weights
        self.transaction_cost = transaction_cost
    
    def threshold_rebalance(self, current_prices: Dict[str, float],
                          threshold: float = 0.05) -> Dict[str, float]:
        """
        Rebalance if weights drift beyond threshold.
        
        Args:
            current_prices: Current prices {symbol: price}
            threshold: Weight drift threshold (e.g., 5%)
        
        Returns:
            rebalance_trades: {symbol: trade_qty} (negative for sell)
        """
        
        # Calculate current weights
        portfolio_value = sum(self.portfolio.get(symbol, 0) * current_prices.get(symbol, 0)
                             for symbol in self.target_weights.keys())
        
        current_weights = {}
        rebalance_needed = False
        
        for symbol in self.target_weights.keys():
            qty = self.portfolio.get(symbol, 0)
            price = current_prices.get(symbol, 1)
            value = qty * price
            weight = value / portfolio_value if portfolio_value > 0 else 0
            current_weights[symbol] = weight
            
            weight_drift = abs(weight - self.target_weights[symbol])
            if weight_drift > threshold:
                rebalance_needed = True
        
        if not rebalance_needed:
            logger.info("📊 No rebalancing needed (within threshold)")
            return {}
        
        # Calculate trades
        trades = {}
        for symbol in self.target_weights.keys():
            current_weight = current_weights.get(symbol, 0)
            target_weight = self.target_weights.get(symbol, 0)
            weight_diff = target_weight - current_weight
            
            # Convert weight diff to quantity
            target_value = weight_diff * portfolio_value
            current_price = current_prices.get(symbol, 1)
            trade_qty = target_value / current_price
            
            trades[symbol] = trade_qty
        
        logger.info(f"✅ Rebalancing needed: {trades}")
        return trades
    
    def time_based_rebalance(self, current_prices: Dict[str, float],
                            rebalance_frequency: str = "monthly") -> Dict[str, float]:
        """
        Rebalance on a fixed schedule.
        
        Args:
            current_prices: Current prices
            rebalance_frequency: "weekly", "monthly", "quarterly", "annual"
        
        Returns:
            rebalance_trades
        """
        
        # In production, would check last rebalance date
        # For now, always return rebalance trades
        
        portfolio_value = sum(self.portfolio.get(symbol, 0) * current_prices.get(symbol, 0)
                             for symbol in self.target_weights.keys())
        
        trades = {}
        for symbol in self.target_weights.keys():
            target_weight = self.target_weights[symbol]
            target_value = target_weight * portfolio_value
            
            current_qty = self.portfolio.get(symbol, 0)
            current_price = current_prices.get(symbol, 1)
            
            target_qty = target_value / current_price
            trade_qty = target_qty - current_qty
            
            trades[symbol] = trade_qty
        
        logger.info(f"✅ {rebalance_frequency.capitalize()} rebalance: {trades}")
        return trades
    
    def momentum_based_rebalance(self, returns: pd.DataFrame,
                                lookback: int = 20) -> Dict[str, float]:
        """
        Rebalance based on momentum of each position.
        
        Args:
            returns: Historical returns
            lookback: Days to look back for momentum
        
        Returns:
            rebalance_trades
        """
        
        # Calculate momentum for each symbol
        momentum = {}
        for symbol in self.target_weights.keys():
            if symbol in returns.columns:
                recent_returns = returns[symbol].tail(lookback)
                momentum[symbol] = recent_returns.sum()
            else:
                momentum[symbol] = 0
        
        # Adjust weights based on momentum
        total_momentum = sum(max(m, 0) for m in momentum.values())
        
        adjusted_weights = {}
        for symbol in self.target_weights.keys():
            if total_momentum > 0:
                adjusted_weights[symbol] = max(momentum.get(symbol, 0), 0) / total_momentum
            else:
                adjusted_weights[symbol] = 1 / len(self.target_weights)
        
        # Calculate trades
        portfolio_value = sum(self.portfolio.get(symbol, 0) * momentum.get(symbol, 1)
                             for symbol in self.target_weights.keys())
        
        trades = {}
        for symbol in self.target_weights.keys():
            target_value = adjusted_weights[symbol] * portfolio_value
            target_qty = target_value / momentum.get(symbol, 1)
            current_qty = self.portfolio.get(symbol, 0)
            trades[symbol] = target_qty - current_qty
        
        logger.info(f"✅ Momentum-based rebalance: {trades}")
        return trades

class PortfolioRebalancer:
    """High-level portfolio rebalancing manager."""
    
    def __init__(self, portfolio: Dict[str, float]):
        self.portfolio = portfolio
        self.markowitz = Markowitz()
        self.rebalance_history = []
    
    def optimize_allocation(self, expected_returns: pd.Series,
                           cov_matrix: np.ndarray,
                           method: str = "markowitz") -> PortfolioWeights:
        """
        Optimize portfolio allocation.
        
        Args:
            expected_returns: Series of expected annual returns
            cov_matrix: Covariance matrix
            method: "markowitz", "riskparity", "equalweight"
        
        Returns:
            Optimized portfolio weights
        """
        
        symbols = list(expected_returns.index)
        returns_array = expected_returns.values
        
        if method == "markowitz":
            weights, ret, vol = self.markowitz.optimal_portfolio(returns_array, cov_matrix)
        elif method == "riskparity":
            weights = RiskParity.allocate(cov_matrix)
            ret = np.dot(weights, returns_array)
            vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        elif method == "equalweight":
            weights = RiskParity.equal_weight(len(symbols))
            ret = np.dot(weights, returns_array)
            vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Create weight dictionary
        allocations = {symbol: float(weight) for symbol, weight in zip(symbols, weights)}
        
        sharpe = (ret - 0.05) / vol if vol > 0 else 0
        
        portfolio_weights = PortfolioWeights(
            allocations=allocations,
            timestamp=datetime.now(),
            rebalance_reason=f"Optimization ({method})",
            expected_return=ret,
            expected_volatility=vol,
            sharpe_ratio=sharpe
        )
        
        self.rebalance_history.append(portfolio_weights)
        
        logger.info(f"✅ Portfolio optimized ({method}): Sharpe={sharpe:.2f}")
        return portfolio_weights

# Example usage
def example_portfolio_rebalancing():
    """Example portfolio rebalancing."""
    
    # Sample portfolio
    portfolio = {
        'NIFTY50': 1,
        'TCS': 10,
        'INFY': 5,
        'RELIANCE': 2
    }
    
    # Expected returns (annual)
    expected_returns = pd.Series({
        'NIFTY50': 0.12,
        'TCS': 0.15,
        'INFY': 0.14,
        'RELIANCE': 0.10
    })
    
    # Covariance matrix
    cov_matrix = np.array([
        [0.04, 0.02, 0.01, 0.015],
        [0.02, 0.06, 0.025, 0.02],
        [0.01, 0.025, 0.05, 0.015],
        [0.015, 0.02, 0.015, 0.03]
    ])
    
    rebalancer = PortfolioRebalancer(portfolio)
    
    # Optimize
    print("📊 Optimizing portfolio...")
    weights_markowitz = rebalancer.optimize_allocation(expected_returns, cov_matrix, "markowitz")
    print(f"Markowitz weights: {weights_markowitz.allocations}")
    print(f"Expected return: {weights_markowitz.expected_return:.2%}")
    print(f"Expected volatility: {weights_markowitz.expected_volatility:.2%}")
    print(f"Sharpe ratio: {weights_markowitz.sharpe_ratio:.2f}")
    
    weights_riskparity = rebalancer.optimize_allocation(expected_returns, cov_matrix, "riskparity")
    print(f"\nRisk parity weights: {weights_riskparity.allocations}")
    
    print("\n✅ Portfolio rebalancing complete!")

if __name__ == "__main__":
    example_portfolio_rebalancing()
