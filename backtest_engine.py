"""High-Performance Backtesting Engine for Strategy Validation."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import json
from dataclasses import dataclass, asdict
from enum import Enum

@dataclass
class Trade:
    """Single trade record."""
    trade_id: int
    symbol: str
    entry_time: datetime
    entry_price: float
    quantity: int
    side: str  # BUY or SELL
    exit_time: datetime = None
    exit_price: float = None
    pnl: float = None
    pnl_pct: float = None
    max_profit: float = 0
    max_loss: float = 0
    duration_minutes: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        data['exit_time'] = self.exit_time.isoformat() if self.exit_time else None
        return data

class BacktestEngine:
    """Institutional-grade backtesting engine."""
    
    def __init__(self, strategy_config: Dict, historical_data: Dict[str, pd.DataFrame]):
        self.config = strategy_config
        self.data = historical_data
        self.trades: List[Trade] = []
        self.equity_curve = []
        self.cash = strategy_config['backtesting']['initial_capital']
        self.initial_capital = self.cash
        self.max_drawdown = 0
        self.trade_count = 0
    
    def backtest(self) -> Dict[str, Any]:
        """Run complete backtest."""
        print("🚀 Starting backtest...")
        
        # Get data
        start_date = pd.to_datetime(self.config['backtesting']['start_date'])
        end_date = pd.to_datetime(self.config['backtesting']['end_date'])
        
        # Simulate trading
        for symbol, df in self.data.items():
            df_filtered = df[(df.index >= start_date) & (df.index <= end_date)]
            self._process_symbol(symbol, df_filtered)
        
        # Calculate metrics
        metrics = self._calculate_metrics()
        return metrics
    
    def _process_symbol(self, symbol: str, df: pd.DataFrame) -> None:
        """Process single symbol."""
        entry_conditions = self.config['parameters']['entry_conditions']
        exit_conditions = self.config['exit_conditions']
        risk_limits = self.config['risk_management']
        
        for idx in range(1, len(df)):
            current_row = df.iloc[idx]
            prev_row = df.iloc[idx - 1]
            
            # Check entry conditions
            if self._check_entry_conditions(current_row, entry_conditions):
                # Check risk limits
                if len(self.trades) < risk_limits['max_open_positions']:
                    entry_price = current_row['Close']
                    self._enter_trade(
                        symbol=symbol,
                        entry_time=current_row.name,
                        entry_price=entry_price,
                        quantity=1
                    )
            
            # Check exit conditions for open trades
            self._check_exits(current_row, exit_conditions)
    
    def _check_entry_conditions(self, row: pd.Series, conditions: Dict) -> bool:
        """Check if entry conditions are met."""
        if conditions['type'] == 'AND':
            for condition in conditions['conditions']:
                if not self._evaluate_condition(row, condition):
                    return False
            return True
        return False
    
    def _evaluate_condition(self, row: pd.Series, condition: Dict) -> bool:
        """Evaluate single condition."""
        indicator = condition.get('indicator')
        operator = condition.get('operator')
        
        # Simplified - in production, calculate actual indicators
        if indicator == 'RSI':
            rsi = self._calculate_rsi(row)
            if operator == 'BETWEEN':
                return condition['values'][0] <= rsi <= condition['values'][1]
        
        return True
    
    def _calculate_rsi(self, row: pd.Series, period: int = 14) -> float:
        """Calculate RSI - simplified."""
        return 50.0  # Placeholder
    
    def _enter_trade(self, symbol: str, entry_time: datetime, entry_price: float, quantity: int) -> None:
        """Enter a trade."""
        self.trade_count += 1
        trade = Trade(
            trade_id=self.trade_count,
            symbol=symbol,
            entry_time=entry_time,
            entry_price=entry_price,
            quantity=quantity,
            side='BUY'
        )
        self.trades.append(trade)
        self.cash -= (entry_price * quantity) + (entry_price * quantity * 0.001)  # 0.1% slippage
    
    def _check_exits(self, current_row: pd.Series, exit_conditions: Dict) -> None:
        """Check and execute exit conditions."""
        current_price = current_row['Close']
        current_time = current_row.name
        
        for trade in [t for t in self.trades if t.exit_time is None]:
            # Check profit target
            pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100
            
            if pnl_pct >= exit_conditions['profit_target']['value']:
                self._exit_trade(trade, current_price, current_time)
            elif pnl_pct <= -exit_conditions['stop_loss']['value']:
                self._exit_trade(trade, current_price, current_time)
    
    def _exit_trade(self, trade: Trade, exit_price: float, exit_time: datetime) -> None:
        """Exit a trade."""
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.pnl = (exit_price - trade.entry_price) * trade.quantity
        trade.pnl_pct = ((exit_price - trade.entry_price) / trade.entry_price) * 100
        trade.duration_minutes = int((exit_time - trade.entry_time).total_seconds() / 60)
        
        self.cash += (exit_price * trade.quantity)
        self.equity_curve.append(self.cash)
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate backtest metrics."""
        closed_trades = [t for t in self.trades if t.exit_time is not None]
        
        total_trades = len(closed_trades)
        wins = len([t for t in closed_trades if t.pnl > 0])
        losses = len([t for t in closed_trades if t.pnl < 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = sum([t.pnl for t in closed_trades if t.pnl])
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Calculate max drawdown
        if self.equity_curve:
            cumulative_returns = np.array(self.equity_curve) / self.initial_capital
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max) / running_max
            max_dd = np.min(drawdown) if len(drawdown) > 0 else 0
        else:
            max_dd = 0
        
        metrics = {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_per_trade": round(avg_pnl, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "final_capital": round(self.cash, 2),
            "total_return_pct": round((self.cash - self.initial_capital) / self.initial_capital * 100, 2),
            "profit_factor": round(sum([t.pnl for t in closed_trades if t.pnl > 0]) / 
                                  abs(sum([t.pnl for t in closed_trades if t.pnl < 0])), 2) 
                            if sum([t.pnl for t in closed_trades if t.pnl < 0]) != 0 else 0,
            "trades": [t.to_dict() for t in closed_trades[:50]]  # Last 50 trades
        }
        
        return metrics

# Example usage
def run_example_backtest():
    """Run example backtest."""
    # Create sample data
    dates = pd.date_range('2024-01-01', '2026-05-27', freq='D')
    np.random.seed(42)
    closes = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
    
    data = {
        'NIFTY50': pd.DataFrame({
            'Open': closes,
            'High': closes + 1,
            'Low': closes - 1,
            'Close': closes,
            'Volume': np.random.randint(1000000, 5000000, len(dates))
        }, index=dates)
    }
    
    config = {
        'parameters': {
            'entry_conditions': {
                'type': 'AND',
                'conditions': [
                    {'indicator': 'RSI', 'operator': 'BETWEEN', 'values': [30, 70]}
                ]
            },
            'strategy_legs': []
        },
        'risk_management': {'max_open_positions': 5},
        'exit_conditions': {
            'profit_target': {'value': 2},
            'stop_loss': {'value': 5}
        },
        'backtesting': {
            'initial_capital': 100000,
            'start_date': '2024-01-01',
            'end_date': '2026-05-27'
        }
    }
    
    engine = BacktestEngine(config, data)
    metrics = engine.backtest()
    
    print("\n📊 Backtest Results:")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate_pct']}%")
    print(f"Total P&L: ₹{metrics['total_pnl']}")
    print(f"Max Drawdown: {metrics['max_drawdown_pct']}%")
    print(f"Final Capital: ₹{metrics['final_capital']}")
    
    return metrics

if __name__ == "__main__":
    results = run_example_backtest()
