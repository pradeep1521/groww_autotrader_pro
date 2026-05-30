"""Broker Factory - Manages all broker implementations."""

import logging
from typing import Dict, Optional, Tuple
from brokers.abstract_broker import AbstractBroker
from brokers.zerodha_broker import ZerodhaBroker
from brokers.groww_broker import GrowwBrokerImpl
from brokers.paper_broker import PaperTradingBroker
from brokers.kotak_neo_broker import KotakNeoBroker

logger = logging.getLogger(__name__)

# Global broker instance
_broker_instance: Optional[AbstractBroker] = None
_broker_type: str = "paper"  # Default to paper trading


class BrokerFactory:
    """Factory for creating and managing broker instances."""
    
    AVAILABLE_BROKERS = {
        'zerodha': ZerodhaBroker,
        'groww': GrowwBrokerImpl,
        'paper': PaperTradingBroker,
        'kotak_neo': KotakNeoBroker,
    }
    
    @staticmethod
    def get_available_brokers() -> Dict[str, str]:
        """Get list of available brokers with descriptions."""
        return {
            'paper': 'Paper Trading (Simulated, ₹100k starting balance)',
            'zerodha': 'Zerodha Kite API (Real trading)',
            'groww': 'Groww Broker (Real trading)',
            'kotak_neo': 'Kotak Neo NeoTrade API (Real trading, ₹0 brokerage)',
        }
    
    @staticmethod
    def create_broker(broker_name: str) -> AbstractBroker:
        """
        Create a broker instance.
        
        Args:
            broker_name: 'zerodha', 'groww', or 'paper'
        
        Returns:
            Broker instance
        
        Raises:
            ValueError: If broker_name is not supported
        """
        broker_name = broker_name.lower()
        
        if broker_name not in BrokerFactory.AVAILABLE_BROKERS:
            raise ValueError(
                f"Unknown broker: {broker_name}. "
                f"Available: {list(BrokerFactory.AVAILABLE_BROKERS.keys())}"
            )
        
        broker_class = BrokerFactory.AVAILABLE_BROKERS[broker_name]
        broker = broker_class()
        
        logger.info(f"Created {broker_name} broker instance")
        return broker
    
    @staticmethod
    def setup_global_broker(broker_name: str, 
                          credentials: Dict[str, str] = None) -> Tuple[bool, str]:
        """
        Set up global broker instance and authenticate.
        
        Args:
            broker_name: 'zerodha', 'groww', or 'paper'
            credentials: Dict with broker credentials
        
        Returns:
            (success, message)
        """
        global _broker_instance, _broker_type
        
        try:
            # Create broker
            broker = BrokerFactory.create_broker(broker_name)
            _broker_instance = broker
            _broker_type = broker_name
            
            # Authenticate
            if credentials:
                success, message = broker.authenticate(credentials)
                if not success:
                    logger.error(f"Failed to authenticate with {broker_name}: {message}")
                    # Fall back to paper trading
                    _broker_instance = BrokerFactory.create_broker('paper')
                    _broker_instance.authenticate({})
                    return False, f"Fallback to paper trading: {message}"
                
                logger.info(f"✅ Successfully authenticated with {broker_name}")
                return True, message
            else:
                # No credentials (paper trading)
                broker.authenticate({})
                logger.info(f"✅ {broker_name} broker ready (no auth needed)")
                return True, f"{broker_name} broker initialized"
        
        except Exception as e:
            logger.error(f"Error setting up broker: {e}")
            # Fall back to paper trading
            try:
                _broker_instance = BrokerFactory.create_broker('paper')
                _broker_instance.authenticate({})
                return False, f"Fallback to paper trading: {str(e)}"
            except Exception as e2:
                logger.error(f"Failed to initialize paper trading: {e2}")
                return False, f"Failed to initialize any broker: {str(e2)}"


def get_broker() -> AbstractBroker:
    """
    Get global broker instance.
    
    Returns current broker or creates paper trading broker if none exists.
    """
    global _broker_instance
    
    if _broker_instance is None:
        _broker_instance = BrokerFactory.create_broker('paper')
        _broker_instance.authenticate({})
        logger.info("Initialized default paper trading broker")
    
    return _broker_instance


def get_broker_type() -> str:
    """Get current broker type."""
    return _broker_type


def switch_broker(broker_name: str, 
                 credentials: Dict[str, str] = None) -> Tuple[bool, str]:
    """
    Switch to different broker.
    
    Args:
        broker_name: 'zerodha', 'groww', or 'paper'
        credentials: Dict with broker credentials
    
    Returns:
        (success, message)
    """
    return BrokerFactory.setup_global_broker(broker_name, credentials)
