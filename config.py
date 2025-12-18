"""
TradeNova Configuration Management
"""
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Config:
    """Configuration class for TradeNova"""
    
    # Alpaca API
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
    ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
    # Remove /v2 from base URL if present (alpaca-trade-api adds it automatically)
    _base_url = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    ALPACA_BASE_URL = _base_url.rstrip('/').rstrip('/v2')
    
    # Massive API (formerly Polygon.io) for options data
    # Supports both MASSIVE_API_KEY and POLYGON_API_KEY for backwards compatibility
    MASSIVE_API_KEY = os.getenv('MASSIVE_API_KEY') or os.getenv('POLYGON_API_KEY', '')
    POLYGON_API_KEY = MASSIVE_API_KEY  # Backwards compatibility alias
    
    # Trading Parameters
    INITIAL_BALANCE = float(os.getenv('INITIAL_BALANCE', '10000'))
    MAX_ACTIVE_TRADES = int(os.getenv('MAX_ACTIVE_TRADES', '10'))
    POSITION_SIZE_PCT = float(os.getenv('POSITION_SIZE_PCT', '0.50'))
    STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', '0.15'))
    
    # Profit Targets
    TP1_PCT = float(os.getenv('TP1_PCT', '0.40'))
    TP1_EXIT_PCT = float(os.getenv('TP1_EXIT_PCT', '0.50'))
    TP2_PCT = float(os.getenv('TP2_PCT', '0.60'))
    TP2_EXIT_PCT = float(os.getenv('TP2_EXIT_PCT', '0.20'))
    TP3_PCT = float(os.getenv('TP3_PCT', '1.00'))
    TP3_EXIT_PCT = float(os.getenv('TP3_EXIT_PCT', '0.10'))
    TP4_PCT = float(os.getenv('TP4_PCT', '1.50'))
    TP4_EXIT_PCT = float(os.getenv('TP4_EXIT_PCT', '0.10'))
    TP5_PCT = float(os.getenv('TP5_PCT', '2.00'))
    TP5_EXIT_PCT = float(os.getenv('TP5_EXIT_PCT', '1.00'))
    
    # Trailing Stop
    TRAILING_STOP_ACTIVATION_PCT = float(os.getenv('TRAILING_STOP_ACTIVATION_PCT', '1.50'))
    TRAILING_STOP_MIN_PROFIT_PCT = float(os.getenv('TRAILING_STOP_MIN_PROFIT_PCT', '1.00'))
    
    # Tickers (SPY excluded - user requirement)
    TICKERS: List[str] = [
        'NVDA', 'AAPL', 'TSLA', 'META', 'GOOG', 
        'MSFT', 'AMZN', 'MSTR', 'AVGO', 'PLTR', 
        'AMD', 'INTC'
    ]
    
    # Options Trading Parameters
    MIN_DTE = int(os.getenv('MIN_DTE', '0'))  # Minimum days to expiration
    MAX_DTE = int(os.getenv('MAX_DTE', '30'))  # Maximum days to expiration (user requirement: 0-30 DTE)
    TARGET_DTE = int(os.getenv('TARGET_DTE', '15'))  # Target DTE for option selection
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        if not cls.ALPACA_API_KEY or not cls.ALPACA_SECRET_KEY:
            raise ValueError("Alpaca API credentials not set in environment variables")
        return True


