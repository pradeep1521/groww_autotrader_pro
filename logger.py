"""Comprehensive logging setup with file and console output."""

import logging
import sys
from pathlib import Path
from config import config

def setup_logger(name: str = "GrowwAutoTrader") -> logging.Logger:
    """Create and configure logger with both file and console handlers."""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler (DEBUG level)
    Path(config.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    
    # Add handlers if not already present
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

# Module-level logger
logger = setup_logger()
