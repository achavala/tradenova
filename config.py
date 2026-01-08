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
    TP5_EXIT_PCT = float(os.getenv('TP5_EXIT_PCT', '0.10'))  # Exit 10% at +200% (changed from 100%)
    
    # Dynamic Trailing Stop (tiered pullback based on peak P&L)
    # Peak P&L > 100% → Allow 10% pullback (tight protection)
    # Peak P&L > 80%  → Allow 12% pullback
    # Peak P&L > 60%  → Allow 15% pullback
    # Peak P&L > 40%  → Allow 18% pullback (standard)
    TRAILING_STOP_TIERS = [
        (1.00, 0.10),  # Peak > 100% → 10% pullback allowed
        (0.80, 0.12),  # Peak > 80% → 12% pullback allowed
        (0.60, 0.15),  # Peak > 60% → 15% pullback allowed
        (0.40, 0.18),  # Peak > 40% → 18% pullback allowed
    ]
    TRAILING_STOP_ACTIVATION_PCT = float(os.getenv('TRAILING_STOP_ACTIVATION_PCT', '0.40'))  # Activate at +40%
    TRAILING_STOP_MIN_PROFIT_PCT = float(os.getenv('TRAILING_STOP_MIN_PROFIT_PCT', '0.20'))  # Minimum +20% profit lock
    
    # Tickers (SPY excluded - user requirement)
    TICKERS: List[str] = [
        # Big Tech & Semis
        'NVDA', 'AAPL', 'TSLA', 'META', 'GOOG', 
        'MSFT', 'AMZN', 'AVGO', 'AMD', 'INTC', 'MU',
        # High Growth / Volatile
        'MSTR', 'PLTR', 'SMCI', 'HOOD', 'COIN',
        # Emerging / Speculative
        'RKLB', 'OKLO', 'PATH', 'NBIS', 'IREN'
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
    
    # ========== PHASE B: THETA + DTE GOVERNANCE ==========
    # DTE-based forced exits (time decay protection)
    DTE_EXIT_RULES = [
        # (max_dte, min_profit_to_hold) - exit if DTE <= max_dte AND profit < min_profit_to_hold
        (1, 0.50),   # < 1 DTE: must have +50% profit to hold, otherwise exit
        (3, 0.20),   # < 3 DTE: must have +20% profit to hold, otherwise exit
        (5, 0.10),   # < 5 DTE: must have +10% profit to hold, otherwise exit
    ]
    
    # DTE-based position sizing (smaller positions for higher risk)
    DTE_POSITION_SIZE_MULTIPLIERS = [
        # (max_dte, size_multiplier) - reduce position size for short DTE
        (3, 0.50),   # 0-3 DTE: 50% of normal size (higher gamma risk)
        (7, 0.75),   # 4-7 DTE: 75% of normal size
        (14, 1.00),  # 8-14 DTE: full size
    ]
    
    # Portfolio theta budget (max daily theta burn in dollars)
    MAX_DAILY_THETA_BURN = float(os.getenv('MAX_DAILY_THETA_BURN', '500'))  # Max $500/day theta decay
    
    # ========== PHASE C: GREEKS & GAMMA CONTROL ==========
    # Portfolio Greeks limits (absolute values)
    MAX_PORTFOLIO_DELTA = float(os.getenv('MAX_PORTFOLIO_DELTA', '500'))    # Max net delta exposure
    MAX_PORTFOLIO_GAMMA = float(os.getenv('MAX_PORTFOLIO_GAMMA', '100'))    # Max gamma exposure
    MAX_PORTFOLIO_THETA = float(os.getenv('MAX_PORTFOLIO_THETA', '-500'))   # Max negative theta (daily decay)
    MAX_PORTFOLIO_VEGA = float(os.getenv('MAX_PORTFOLIO_VEGA', '200'))      # Max vega exposure
    
    # Position-level gamma limits
    MAX_POSITION_GAMMA = float(os.getenv('MAX_POSITION_GAMMA', '50'))  # Max gamma per position
    
    # ========== PHASE D: IV ENFORCEMENT & STRIKE SELECTION ==========
    # IV Rank gate (only buy options when IV is relatively low)
    MAX_IV_RANK_FOR_ENTRY = float(os.getenv('MAX_IV_RANK_FOR_ENTRY', '50'))  # Only enter if IV Rank < 50%
    MIN_IV_RANK_FOR_ENTRY = float(os.getenv('MIN_IV_RANK_FOR_ENTRY', '10'))  # Avoid extremely low IV (no movement)
    
    # Delta-based strike selection
    DELTA_SELECTION_RULES = [
        # (min_confidence, max_confidence, target_delta_range)
        (0.90, 1.00, (0.50, 0.70)),  # High confidence: ITM (delta 0.50-0.70)
        (0.80, 0.90, (0.35, 0.55)),  # Medium confidence: ATM (delta 0.35-0.55)
        (0.60, 0.80, (0.20, 0.40)),  # Lower confidence: slightly OTM (delta 0.20-0.40)
    ]
    DEFAULT_TARGET_DELTA = (0.35, 0.55)  # Default: ATM range
    
    # ========== PHASE E: EXECUTION OPTIMIZATION ==========
    # Limit order settings
    USE_LIMIT_ORDERS = bool(os.getenv('USE_LIMIT_ORDERS', 'True').lower() == 'true')
    LIMIT_ORDER_OFFSET_PCT = float(os.getenv('LIMIT_ORDER_OFFSET_PCT', '0.02'))  # 2% better than mid
    LIMIT_ORDER_TIMEOUT_SECONDS = int(os.getenv('LIMIT_ORDER_TIMEOUT_SECONDS', '30'))  # Chase after 30s
    
    # Time-of-day restrictions (ET timezone)
    AVOID_FIRST_MINUTES = int(os.getenv('AVOID_FIRST_MINUTES', '30'))   # Avoid first 30 min (9:30-10:00)
    AVOID_LAST_MINUTES = int(os.getenv('AVOID_LAST_MINUTES', '15'))     # Avoid last 15 min (3:45-4:00)
    OPTIMAL_TRADING_START = "10:00"  # Best liquidity starts at 10 AM ET
    OPTIMAL_TRADING_END = "15:45"    # Best liquidity ends at 3:45 PM ET
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        if not cls.ALPACA_API_KEY or not cls.ALPACA_SECRET_KEY:
            raise ValueError("Alpaca API credentials not set in environment variables")
        return True


