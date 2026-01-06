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
    
    # Alpha Vantage API for earnings calendar (optional)
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')
    
    # Trading Parameters
    INITIAL_BALANCE = float(os.getenv('INITIAL_BALANCE', '10000'))
    MAX_ACTIVE_TRADES = int(os.getenv('MAX_ACTIVE_TRADES', '10'))
    POSITION_SIZE_PCT = float(os.getenv('POSITION_SIZE_PCT', '0.10'))  # 10% max per position (was 50%!)
    STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', '0.20'))  # 20% stop-loss per position
    
    # Risk Management (CRITICAL)
    MAX_POSITION_PCT = float(os.getenv('MAX_POSITION_PCT', '0.10'))  # Hard cap: 10% of portfolio per position
    MAX_PORTFOLIO_HEAT = float(os.getenv('MAX_PORTFOLIO_HEAT', '0.35'))  # Max 35% total options exposure
    MAX_CORRELATED_EXPOSURE = float(os.getenv('MAX_CORRELATED_EXPOSURE', '0.25'))  # Max 25% in correlated assets
    MAX_CONTRACTS_PER_TRADE = int(os.getenv('MAX_CONTRACTS_PER_TRADE', '10'))  # Hard cap: 10 contracts per trade
    
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
    # DTE Range: 0-14 days (0 DTE allowed - close positions on profit)
    # User prefers closing positions when profitable rather than holding
    MIN_DTE = int(os.getenv('MIN_DTE', '0'))  # Allow 0 DTE - close on profit
    MAX_DTE = int(os.getenv('MAX_DTE', '14'))  # Maximum 14 days (was 30 - too much time decay variance)
    TARGET_DTE = int(os.getenv('TARGET_DTE', '10'))  # Target ~10 DTE for optimal gamma/theta balance
    
    # Short-term options (0-6 DTE) - only for high confidence
    MIN_DTE_SHORT_TERM = int(os.getenv('MIN_DTE_SHORT_TERM', '0'))
    MAX_DTE_SHORT_TERM = int(os.getenv('MAX_DTE_SHORT_TERM', '6'))
    SHORT_TERM_CONFIDENCE_THRESHOLD = float(os.getenv('SHORT_TERM_CONFIDENCE_THRESHOLD', '0.90'))  # 90%+ confidence only
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        if not cls.ALPACA_API_KEY or not cls.ALPACA_SECRET_KEY:
            raise ValueError("Alpaca API credentials not set in environment variables")
        return True


