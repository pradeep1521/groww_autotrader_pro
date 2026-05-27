"""Institutional Strategy Configuration Format - JSON Schema."""

import json
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

# Example JSON strategy configuration
STRATEGY_TEMPLATE = {
    "metadata": {
        "name": "Iron Condor - NIFTY",
        "description": "Sell OTM call + put spreads",
        "version": "1.0",
        "author": "Strategy Team",
        "created_at": "2026-05-27"
    },
    
    "universe": {
        "symbols": ["NIFTY50"],
        "market": "NSE",
        "asset_class": "INDEX_OPTIONS"
    },
    
    "parameters": {
        "entry_conditions": {
            "type": "AND",
            "conditions": [
                {
                    "indicator": "RSI",
                    "period": 14,
                    "operator": "BETWEEN",
                    "values": [40, 60]
                },
                {
                    "indicator": "ATR",
                    "period": 20,
                    "operator": "GT",
                    "value": 100
                }
            ]
        },
        
        "strategy_legs": [
            {
                "leg_id": 1,
                "position": "SELL_CALL",
                "strike_offset": 1,
                "expiry_days": 7,
                "quantity": 1,
                "side": "SHORT"
            },
            {
                "leg_id": 2,
                "position": "BUY_CALL",
                "strike_offset": 2,
                "expiry_days": 7,
                "quantity": 1,
                "side": "LONG"
            },
            {
                "leg_id": 3,
                "position": "SELL_PUT",
                "strike_offset": -1,
                "expiry_days": 7,
                "quantity": 1,
                "side": "SHORT"
            },
            {
                "leg_id": 4,
                "position": "BUY_PUT",
                "strike_offset": -2,
                "expiry_days": 7,
                "quantity": 1,
                "side": "LONG"
            }
        ]
    },
    
    "risk_management": {
        "max_position_size": 10,
        "max_loss_per_trade": 5000,
        "max_daily_loss": 25000,
        "max_open_positions": 5,
        "max_exposure_pct": 10,
        "Greeks_limits": {
            "delta_max": 0.3,
            "gamma_max": 0.05,
            "theta_min": 0.5,
            "vega_max": 100
        }
    },
    
    "exit_conditions": {
        "profit_target": {
            "type": "PERCENT",
            "value": 50
        },
        "stop_loss": {
            "type": "PERCENT",
            "value": 100
        },
        "time_exit": {
            "days_to_expiry": 1,
            "action": "CLOSE"
        }
    },
    
    "execution": {
        "order_type": "LIMIT",
        "slippage_pct": 0.1,
        "max_execution_time_seconds": 30,
        "partial_fill_allowed": True,
        "broker_selection": "LOWEST_SLIPPAGE"
    },
    
    "backtesting": {
        "start_date": "2024-01-01",
        "end_date": "2026-05-27",
        "initial_capital": 100000,
        "brokerage_pct": 0.1,
        "slippage_bps": 5,
        "commission_per_trade": 50
    }
}

class StrategyConfig:
    """Parse and validate strategy JSON configuration."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.config = config_dict
        self.validate()
    
    def validate(self) -> bool:
        """Validate strategy configuration."""
        required_keys = ["metadata", "universe", "parameters", "risk_management", "exit_conditions"]
        
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required key: {key}")
        
        # Validate legs
        legs = self.config.get("parameters", {}).get("strategy_legs", [])
        if not legs:
            raise ValueError("At least one strategy leg required")
        
        return True
    
    def get_legs(self) -> List[Dict]:
        """Get strategy legs."""
        return self.config["parameters"]["strategy_legs"]
    
    def get_entry_conditions(self) -> Dict:
        """Get entry conditions."""
        return self.config["parameters"]["entry_conditions"]
    
    def get_risk_limits(self) -> Dict:
        """Get risk management limits."""
        return self.config["risk_management"]
    
    def to_json(self) -> str:
        """Export as JSON."""
        return json.dumps(self.config, indent=2)
    
    @staticmethod
    def from_json(json_str: str) -> 'StrategyConfig':
        """Load from JSON string."""
        config_dict = json.loads(json_str)
        return StrategyConfig(config_dict)
    
    @staticmethod
    def from_file(file_path: str) -> 'StrategyConfig':
        """Load from JSON file."""
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        return StrategyConfig(config_dict)

# Example usage
if __name__ == "__main__":
    # Create config from template
    config = StrategyConfig(STRATEGY_TEMPLATE)
    print("✅ Strategy config valid")
    print(f"\nStrategy: {config.config['metadata']['name']}")
    print(f"Legs: {len(config.get_legs())}")
    print(f"Risk limits: {config.get_risk_limits()}")
