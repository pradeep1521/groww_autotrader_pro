"""Strategy Comparison - Compare multiple backtests side-by-side."""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class StrategyMetrics:
    """Strategy performance metrics."""
    name: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_return: float
    best_trade: float
    worst_trade: float
    consecutive_wins: int
    consecutive_losses: int
    recovery_factor: float

class StrategyComparison:
    """Compare multiple strategies side-by-side."""
    
    def __init__(self):
        self.strategies: Dict[str, Dict[str, Any]] = {}
    
    def add_strategy(self, name: str, trades: List[Dict[str, Any]],
                    capital: float = 100000, risk_free_rate: float = 0.05) -> None:
        """Add strategy with its trades for comparison."""
        
        metrics = self._calculate_metrics(trades, capital, risk_free_rate)
        self.strategies[name] = {
            'trades': trades,
            'metrics': metrics,
            'capital': capital
        }
    
    def _calculate_metrics(self, trades: List[Dict[str, Any]], 
                          capital: float, risk_free_rate: float) -> StrategyMetrics:
        """Calculate comprehensive metrics from trades."""
        
        if not trades:
            return StrategyMetrics(
                name="", total_return=0, annual_return=0, sharpe_ratio=0,
                sortino_ratio=0, max_drawdown=0, win_rate=0, profit_factor=0,
                total_trades=0, avg_trade_return=0, best_trade=0, worst_trade=0,
                consecutive_wins=0, consecutive_losses=0, recovery_factor=0
            )
        
        # Calculate returns
        pnl_values = [t.get('pnl', 0) for t in trades]
        total_pnl = sum(pnl_values)
        total_return = total_pnl / capital
        
        # Annual return (assuming 252 trading days)
        trading_days = (trades[-1].get('close_date', datetime.now()) - 
                       trades[0].get('open_date', datetime.now())).days
        years = max(trading_days / 252, 1)
        annual_return = (1 + total_return) ** (1 / years) - 1
        
        # Win rate
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        win_rate = winning_trades / len(trades) if trades else 0
        
        # Profit factor
        total_wins = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0)
        total_losses = abs(sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) < 0))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Best/worst trade
        best_trade = max(pnl_values) if pnl_values else 0
        worst_trade = min(pnl_values) if pnl_values else 0
        avg_trade_return = np.mean(pnl_values) if pnl_values else 0
        
        # Consecutive wins/losses
        consecutive_wins = max(self._consecutive_count(trades, True), 0)
        consecutive_losses = max(self._consecutive_count(trades, False), 0)
        
        # Drawdown
        cumulative = np.cumsum([0] + pnl_values)
        running_max = np.maximum.accumulate(cumulative)
        # Avoid division by zero when running_max is 0
        with np.errstate(divide='ignore', invalid='ignore'):
            drawdown = np.where(running_max != 0, (cumulative - running_max) / running_max, 0)
        max_drawdown = abs(np.nanmin(drawdown)) if not np.isnan(np.nanmin(drawdown)) else 0
        
        # Sharpe ratio
        returns = np.array(pnl_values) / capital
        sharpe_ratio = self._calc_sharpe(returns, risk_free_rate)
        
        # Sortino ratio
        sortino_ratio = self._calc_sortino(returns, risk_free_rate)
        
        # Recovery factor
        recovery_factor = total_pnl / (max_drawdown * capital) if max_drawdown > 0 else 0
        
        return StrategyMetrics(
            name="",
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(trades),
            avg_trade_return=avg_trade_return,
            best_trade=best_trade,
            worst_trade=worst_trade,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            recovery_factor=recovery_factor
        )
    
    def comparison_table(self) -> pd.DataFrame:
        """Generate comparison table of all strategies."""
        
        data = []
        
        for name, strategy in self.strategies.items():
            metrics = strategy['metrics']
            data.append({
                'Strategy': name,
                'Total Return': f"{metrics.total_return * 100:.2f}%",
                'Annual Return': f"{metrics.annual_return * 100:.2f}%",
                'Sharpe': f"{metrics.sharpe_ratio:.2f}",
                'Sortino': f"{metrics.sortino_ratio:.2f}",
                'Max DD': f"{metrics.max_drawdown * 100:.2f}%",
                'Win Rate': f"{metrics.win_rate * 100:.1f}%",
                'Profit Factor': f"{metrics.profit_factor:.2f}",
                'Total Trades': metrics.total_trades,
                'Avg Trade': f"₹{metrics.avg_trade_return:.0f}",
                'Best Trade': f"₹{metrics.best_trade:.0f}",
                'Worst Trade': f"₹{metrics.worst_trade:.0f}"
            })
        
        return pd.DataFrame(data)
    
    def ranking(self) -> pd.DataFrame:
        """Rank strategies by different metrics."""
        
        rankings = {}
        
        metrics_to_rank = [
            ('total_return', False),      # Higher is better
            ('sharpe_ratio', False),      # Higher is better
            ('win_rate', False),          # Higher is better
            ('max_drawdown', True),       # Lower is better
            ('recovery_factor', False)    # Higher is better
        ]
        
        for metric, lower_is_better in metrics_to_rank:
            values = [(name, getattr(s['metrics'], metric)) 
                     for name, s in self.strategies.items()]
            
            if lower_is_better:
                sorted_values = sorted(values, key=lambda x: x[1])
            else:
                sorted_values = sorted(values, key=lambda x: x[1], reverse=True)
            
            rankings[metric] = [name for name, _ in sorted_values]
        
        # Create ranking table
        rank_data = []
        for i, name in enumerate(rankings['total_return']):
            rank_data.append({
                'Rank': i + 1,
                'Strategy': name,
                'By Return': 1,
                'By Sharpe': list(rankings['sharpe_ratio']).index(name) + 1,
                'By Win Rate': list(rankings['win_rate']).index(name) + 1,
                'By Drawdown': list(rankings['max_drawdown']).index(name) + 1,
                'By Recovery': list(rankings['recovery_factor']).index(name) + 1
            })
        
        return pd.DataFrame(rank_data)
    
    def equity_curve_comparison(self) -> Dict[str, List[float]]:
        """Generate equity curves for all strategies."""
        
        curves = {}
        
        for name, strategy in self.strategies.items():
            trades = strategy['trades']
            pnl_values = [0] + [t.get('pnl', 0) for t in trades]
            equity = strategy['capital'] + np.cumsum(pnl_values)
            curves[name] = equity.tolist()
        
        return curves
    
    def drawdown_comparison(self) -> Dict[str, List[float]]:
        """Calculate drawdown for each strategy."""
        
        drawdowns = {}
        
        for name, strategy in self.strategies.items():
            trades = strategy['trades']
            pnl_values = [t.get('pnl', 0) for t in trades]
            cumulative = strategy['capital'] + np.cumsum([0] + pnl_values)
            running_max = np.maximum.accumulate(cumulative)
            dd = (cumulative - running_max) / running_max * 100
            drawdowns[name] = dd.tolist()
        
        return drawdowns
    
    def monthly_returns(self) -> Dict[str, pd.DataFrame]:
        """Calculate monthly returns for each strategy."""
        
        monthly = {}
        
        for name, strategy in self.strategies.items():
            trades = strategy['trades']
            
            # Group trades by month
            monthly_pnl = {}
            for trade in trades:
                month = trade.get('close_date', datetime.now()).strftime('%Y-%m')
                if month not in monthly_pnl:
                    monthly_pnl[month] = 0
                monthly_pnl[month] += trade.get('pnl', 0)
            
            # Convert to DataFrame
            df = pd.DataFrame(list(monthly_pnl.items()), 
                            columns=['Month', 'PnL'])
            df['Return%'] = df['PnL'] / strategy['capital'] * 100
            monthly[name] = df
        
        return monthly
    
    @staticmethod
    def _consecutive_count(trades: List[Dict], winning: bool = True) -> int:
        """Count consecutive wins or losses."""
        
        max_count = 0
        current_count = 0
        
        for trade in trades:
            is_win = trade.get('pnl', 0) > 0
            
            if (is_win and winning) or (not is_win and not winning):
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        
        return max_count
    
    @staticmethod
    def _calc_sharpe(returns: np.ndarray, risk_free_rate: float) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0
        
        excess_returns = returns - (risk_free_rate / 252)
        return np.mean(excess_returns) / (np.std(excess_returns) + 1e-9) * np.sqrt(252)
    
    @staticmethod
    def _calc_sortino(returns: np.ndarray, risk_free_rate: float) -> float:
        """Calculate Sortino ratio."""
        if len(returns) < 2:
            return 0
        
        excess_returns = returns - (risk_free_rate / 252)
        downside_returns = np.where(excess_returns < 0, excess_returns, 0)
        downside_std = np.std(downside_returns)
        
        return np.mean(excess_returns) / (downside_std + 1e-9) * np.sqrt(252)

# Example usage
def example_strategy_comparison():
    """Example comparing multiple strategies."""
    
    comparison = StrategyComparison()
    
    # Strategy 1: Momentum
    trades_momentum = [
        {'pnl': 5000, 'open_date': datetime(2025, 1, 1), 'close_date': datetime(2025, 1, 5)},
        {'pnl': -2000, 'open_date': datetime(2025, 1, 6), 'close_date': datetime(2025, 1, 8)},
        {'pnl': 8000, 'open_date': datetime(2025, 1, 9), 'close_date': datetime(2025, 1, 15)},
        {'pnl': 3000, 'open_date': datetime(2025, 1, 16), 'close_date': datetime(2025, 1, 20)},
    ]
    
    # Strategy 2: Mean Reversion
    trades_mean_reversion = [
        {'pnl': 3000, 'open_date': datetime(2025, 1, 1), 'close_date': datetime(2025, 1, 3)},
        {'pnl': 4000, 'open_date': datetime(2025, 1, 4), 'close_date': datetime(2025, 1, 7)},
        {'pnl': 2000, 'open_date': datetime(2025, 1, 8), 'close_date': datetime(2025, 1, 11)},
        {'pnl': -1000, 'open_date': datetime(2025, 1, 12), 'close_date': datetime(2025, 1, 14)},
        {'pnl': 6000, 'open_date': datetime(2025, 1, 15), 'close_date': datetime(2025, 1, 20)},
    ]
    
    # Strategy 3: Options
    trades_options = [
        {'pnl': 2000, 'open_date': datetime(2025, 1, 1), 'close_date': datetime(2025, 1, 10)},
        {'pnl': 1500, 'open_date': datetime(2025, 1, 11), 'close_date': datetime(2025, 1, 20)},
    ]
    
    comparison.add_strategy("Momentum", trades_momentum)
    comparison.add_strategy("Mean Reversion", trades_mean_reversion)
    comparison.add_strategy("Options", trades_options)
    
    print("📊 STRATEGY COMPARISON")
    print("=" * 120)
    print(comparison.comparison_table().to_string(index=False))
    
    print("\n🏆 STRATEGY RANKING")
    print("=" * 80)
    print(comparison.ranking().to_string(index=False))
    
    print("\n✅ Strategy comparison complete!")

if __name__ == "__main__":
    example_strategy_comparison()
