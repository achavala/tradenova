"""
Data Validator
Enforces data freshness and source validation per Architect 3 & 4 recommendations

CRITICAL: Prevents trading on stale/delayed data that could poison signals
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import pytz
import pandas as pd

logger = logging.getLogger(__name__)

ET = pytz.timezone('America/New_York')
UTC = pytz.UTC


class DataFreshnessError(Exception):
    """Raised when data is too stale for trading"""
    pass


class DataSourceError(Exception):
    """Raised when wrong data source is used"""
    pass


class DataValidator:
    """
    Validates data freshness and source integrity
    
    CRITICAL RULE (Architect 3 & 4):
    - Massive MUST be the ONLY source for signal data
    - Alpaca is ONLY for execution + account/positions
    - If Massive data unavailable → SKIP ticker, do NOT fallback to Alpaca delayed
    """
    
    # Maximum bar age in seconds before rejecting
    MAX_BAR_AGE_SECONDS = 60  # 1 minute
    
    # Maximum quote age in seconds
    MAX_QUOTE_AGE_SECONDS = 30
    
    def __init__(self, is_paper_mode: bool = True):
        """
        Initialize validator
        
        Args:
            is_paper_mode: If True, enforce strict Massive-only rule
        """
        self.is_paper_mode = is_paper_mode
        self.stale_ticker_count: Dict[str, int] = {}
        self.rejected_tickers: Dict[str, str] = {}
        
        if is_paper_mode:
            logger.warning("=" * 60)
            logger.warning("DATA VALIDATOR: PAPER MODE - Strict data source enforcement")
            logger.warning("Massive REQUIRED for all signal data")
            logger.warning("Alpaca delayed data will be REJECTED for signals")
            logger.warning("=" * 60)
    
    def validate_bar_freshness(
        self, 
        symbol: str, 
        bar_timestamp: datetime, 
        source: str = "unknown"
    ) -> Tuple[bool, str, int]:
        """
        Validate that bar data is fresh enough for trading
        
        Args:
            symbol: Ticker symbol
            bar_timestamp: Timestamp of the latest bar
            source: Data source name (e.g., "massive", "alpaca")
            
        Returns:
            (is_fresh, reason, age_seconds)
        """
        now = datetime.now(UTC)
        
        # Ensure bar_timestamp is timezone-aware
        if bar_timestamp.tzinfo is None:
            bar_timestamp = UTC.localize(bar_timestamp)
        else:
            bar_timestamp = bar_timestamp.astimezone(UTC)
        
        age = (now - bar_timestamp).total_seconds()
        
        # Log bar age for monitoring
        logger.debug(f"[{symbol}] Bar age: {age:.0f}s | Source: {source}")
        
        # Check if from Alpaca Paper (delayed data)
        if self.is_paper_mode and source.lower() == "alpaca":
            reason = f"REJECTED: Alpaca delayed data not allowed for signals in paper mode"
            logger.warning(f"[{symbol}] {reason}")
            self.rejected_tickers[symbol] = reason
            return False, reason, int(age)
        
        # Check bar age
        if age > self.MAX_BAR_AGE_SECONDS:
            reason = f"STALE BAR: {age:.0f}s old > {self.MAX_BAR_AGE_SECONDS}s max"
            logger.warning(f"[{symbol}] {reason}")
            
            # Track stale count
            self.stale_ticker_count[symbol] = self.stale_ticker_count.get(symbol, 0) + 1
            
            return False, reason, int(age)
        
        return True, "Fresh", int(age)
    
    def validate_bars_dataframe(
        self, 
        symbol: str, 
        df: pd.DataFrame, 
        source: str = "unknown"
    ) -> Tuple[bool, str, int]:
        """
        Validate a DataFrame of bars
        
        Args:
            symbol: Ticker symbol
            df: DataFrame with timestamp column or index
            source: Data source name
            
        Returns:
            (is_fresh, reason, age_seconds)
        """
        if df is None or len(df) == 0:
            return False, "No data available", -1
        
        # Get latest timestamp
        if isinstance(df.index, pd.DatetimeIndex):
            latest_ts = df.index[-1]
        elif 'timestamp' in df.columns:
            latest_ts = df['timestamp'].iloc[-1]
        else:
            return False, "No timestamp found in data", -1
        
        # Convert to datetime if needed
        if isinstance(latest_ts, str):
            latest_ts = pd.to_datetime(latest_ts)
        
        # Make timezone-aware
        if latest_ts.tzinfo is None:
            latest_ts = UTC.localize(latest_ts.to_pydatetime())
        else:
            latest_ts = latest_ts.to_pydatetime().astimezone(UTC)
        
        return self.validate_bar_freshness(symbol, latest_ts, source)
    
    def validate_quote_freshness(
        self,
        symbol: str,
        quote_timestamp: datetime,
        source: str = "unknown"
    ) -> Tuple[bool, str, int]:
        """
        Validate quote freshness
        
        Args:
            symbol: Ticker symbol
            quote_timestamp: Timestamp of the quote
            source: Data source name
            
        Returns:
            (is_fresh, reason, age_seconds)
        """
        now = datetime.now(UTC)
        
        if quote_timestamp.tzinfo is None:
            quote_timestamp = UTC.localize(quote_timestamp)
        else:
            quote_timestamp = quote_timestamp.astimezone(UTC)
        
        age = (now - quote_timestamp).total_seconds()
        
        if age > self.MAX_QUOTE_AGE_SECONDS:
            reason = f"STALE QUOTE: {age:.0f}s old > {self.MAX_QUOTE_AGE_SECONDS}s max"
            logger.warning(f"[{symbol}] {reason}")
            return False, reason, int(age)
        
        return True, "Fresh quote", int(age)
    
    def validate_data_source(self, source: str) -> Tuple[bool, str]:
        """
        Validate that data source is acceptable for signals
        
        Args:
            source: Data source name
            
        Returns:
            (is_valid, reason)
        """
        allowed_sources = ["massive", "polygon", "realtime"]
        
        if self.is_paper_mode:
            if source.lower() in ["alpaca", "alpaca_paper", "sip_delayed"]:
                return False, f"REJECTED: {source} not allowed for signals in paper mode"
        
        return True, f"Source {source} accepted"
    
    def should_skip_ticker(self, symbol: str) -> Tuple[bool, str]:
        """
        Check if ticker should be skipped due to repeated data issues
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            (should_skip, reason)
        """
        # Skip if rejected in this cycle
        if symbol in self.rejected_tickers:
            return True, self.rejected_tickers[symbol]
        
        # Skip if repeatedly stale (3+ times)
        if self.stale_ticker_count.get(symbol, 0) >= 3:
            return True, f"Skipped: {symbol} has {self.stale_ticker_count[symbol]} stale data events"
        
        return False, ""
    
    def reset_cycle(self):
        """Reset per-cycle tracking"""
        self.rejected_tickers.clear()
    
    def get_data_quality_report(self) -> Dict:
        """Get report on data quality issues"""
        return {
            "stale_tickers": self.stale_ticker_count,
            "rejected_tickers": self.rejected_tickers,
            "max_bar_age_seconds": self.MAX_BAR_AGE_SECONDS,
            "max_quote_age_seconds": self.MAX_QUOTE_AGE_SECONDS,
            "paper_mode": self.is_paper_mode
        }


def validate_bar_age(bars: pd.DataFrame, symbol: str, max_age_seconds: int = 60) -> Tuple[bool, int]:
    """
    Simple function to validate bar age
    
    Args:
        bars: DataFrame with timestamp
        symbol: Symbol for logging
        max_age_seconds: Maximum allowed age
        
    Returns:
        (is_valid, age_seconds)
    """
    if bars is None or len(bars) == 0:
        logger.warning(f"[{symbol}] No bars data")
        return False, -1
    
    # Get latest timestamp
    if isinstance(bars.index, pd.DatetimeIndex):
        latest_ts = bars.index[-1]
    elif 'timestamp' in bars.columns:
        latest_ts = bars['timestamp'].iloc[-1]
    else:
        logger.warning(f"[{symbol}] No timestamp in bars")
        return False, -1
    
    # Calculate age
    now = datetime.now(UTC)
    if hasattr(latest_ts, 'tz') and latest_ts.tz is None:
        latest_ts = UTC.localize(latest_ts.to_pydatetime())
    elif hasattr(latest_ts, 'tzinfo') and latest_ts.tzinfo is None:
        latest_ts = UTC.localize(latest_ts)
    else:
        latest_ts = pd.Timestamp(latest_ts).tz_convert(UTC)
    
    age = (now - latest_ts).total_seconds()
    
    is_valid = age <= max_age_seconds
    
    if not is_valid:
        logger.warning(f"[{symbol}] Bar age {age:.0f}s exceeds max {max_age_seconds}s")
    else:
        logger.debug(f"[{symbol}] Bar age {age:.0f}s OK")
    
    return is_valid, int(age)


# Singleton instance
data_validator = DataValidator(is_paper_mode=True)  # Default to paper mode

