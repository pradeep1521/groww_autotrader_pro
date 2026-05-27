"""Configuration management with validation."""

import os
from dotenv import load_dotenv
from pathlib import Path
from dataclasses import dataclass

load_dotenv()

@dataclass
class AppConfig:
    """Application configuration with environment variables."""
    
    # API Credentials
    GROWW_ACCESS_TOKEN: str = os.getenv("GROWW_ACCESS_TOKEN", "")
    GROWW_API_KEY: str = os.getenv("GROWW_API_KEY", "")
    GROWW_API_SECRET: str = os.getenv("GROWW_API_SECRET", "")
    
    # Mode & Trading Settings
    APP_MODE: str = os.getenv("APP_MODE", "paper").lower()  # paper | live
    DEFAULT_RISK_PER_TRADE: float = float(os.getenv("DEFAULT_RISK_PER_TRADE", 500))
    MAX_OPEN_POSITIONS: int = int(os.getenv("MAX_OPEN_POSITIONS", 5))
    DAILY_LOSS_LIMIT: float = float(os.getenv("DAILY_LOSS_LIMIT", 5000))
    
    # Screener Settings
    SCREENER_UNIVERSE: str = os.getenv("SCREENER_UNIVERSE", "nifty50")
    SCREENER_SCAN_INTERVAL: int = int(os.getenv("SCREENER_SCAN_INTERVAL", 900))
    SCREENER_ENABLED: bool = os.getenv("SCREENER_ENABLED", "true").lower() == "true"
    
    # Database
    DB_PATH: str = os.getenv("DB_PATH", "./data/trades.db")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "./logs/trader.log")
    
    # Market Hours (IST)
    MARKET_OPEN_TIME: str = os.getenv("MARKET_OPEN_TIME", "09:15")
    MARKET_CLOSE_TIME: str = os.getenv("MARKET_CLOSE_TIME", "15:30")
    MARKET_PRE_CLOSE_TIME: str = os.getenv("MARKET_PRE_CLOSE_TIME", "15:20")
    
    @property
    def is_live_mode(self) -> bool:
        """Check if running in live trading mode."""
        return self.APP_MODE == "live"
    
    @property
    def is_paper_mode(self) -> bool:
        """Check if running in paper trading mode."""
        return self.APP_MODE == "paper"
    
    def validate(self) -> tuple[bool, str]:
        """Validate configuration and return (is_valid, message)."""
        if self.is_live_mode:
            if not self.GROWW_ACCESS_TOKEN:
                return False, "Live mode requires GROWW_ACCESS_TOKEN"
        
        if self.DEFAULT_RISK_PER_TRADE <= 0:
            return False, "DEFAULT_RISK_PER_TRADE must be positive"
        
        if self.MAX_OPEN_POSITIONS <= 0:
            return False, "MAX_OPEN_POSITIONS must be positive"
        
        if self.DAILY_LOSS_LIMIT <= 0:
            return False, "DAILY_LOSS_LIMIT must be positive"
        
        if self.SCREENER_SCAN_INTERVAL < 60:
            return False, "SCREENER_SCAN_INTERVAL must be >= 60 seconds"
        
        return True, "Configuration valid"

# Global config instance
config = AppConfig()

# Create necessary directories
Path(Path(config.DB_PATH).parent).mkdir(parents=True, exist_ok=True)
Path(Path(config.LOG_FILE).parent).mkdir(parents=True, exist_ok=True)
