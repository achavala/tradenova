"""
IV Rank Service
Complete IV Rank integration connecting IV Calculator, Options Data Feed, and History Database
"""
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from services.iv_calculator import IVCalculator
from services.iv_history_db import IVHistoryDB
from services.polygon_options_feed import MassiveOptionsFeed
from config import Config

logger = logging.getLogger(__name__)

class IVRankService:
    """
    Complete IV Rank service
    
    Features:
    - Collects IV data from Massive API
    - Stores in database
    - Calculates IV Rank and Percentile
    - Provides real-time IV metrics
    """
    
    def __init__(
        self,
        options_feed: Optional[MassiveOptionsFeed] = None,
        db_path: Optional[str] = None,
        lookback_days: int = 365
    ):
        """
        Initialize IV Rank service
        
        Args:
            options_feed: Massive options feed (creates if None)
            db_path: Path to IV history database
            lookback_days: Days to look back for IV Rank (default: 365 for 52-week)
        """
        self.options_feed = options_feed or MassiveOptionsFeed()
        self.iv_db = IVHistoryDB(db_path)
        self.iv_calculator = IVCalculator(lookback_days=lookback_days)
        self.lookback_days = lookback_days
    
    def collect_and_store_iv(
        self,
        symbol: str,
        target_dte: int = 15,
        option_type: str = 'call'
    ) -> bool:
        """
        Collect current IV from options data and store in database
        
        Args:
            symbol: Stock symbol
            target_dte: Target days to expiration (default: 15)
            option_type: 'call' or 'put' (default: 'call')
            
        Returns:
            True if collected and stored successfully
        """
        try:
            # Get current price
            current_price = self.options_feed._get_current_stock_price(symbol)
            if not current_price:
                logger.warning(f"Could not get current price for {symbol}")
                return False
            
            # Get expiration dates
            expirations = self.options_feed.get_expiration_dates(symbol)
            if not expirations:
                logger.warning(f"No expiration dates found for {symbol}")
                return False
            
            # Find expiration closest to target DTE
            today = datetime.now().date()
            best_expiration = None
            best_dte_diff = float('inf')
            
            for exp_str in expirations:
                try:
                    exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
                    dte = (exp_date - today).days
                    
                    # Filter to 0-30 DTE range
                    if 0 <= dte <= 30:
                        dte_diff = abs(dte - target_dte)
                        if dte_diff < best_dte_diff:
                            best_dte_diff = dte_diff
                            best_expiration = exp_str
                except:
                    continue
            
            if not best_expiration:
                logger.warning(f"No valid expiration found for {symbol} in 0-30 DTE range")
                return False
            
            # Get ATM option
            atm_option = self.options_feed.get_atm_options(
                symbol,
                best_expiration,
                option_type,
                current_price=current_price
            )
            
            if not atm_option:
                logger.warning(f"Could not get ATM option for {symbol}")
                return False
            
            # Extract IV
            iv = atm_option.get('implied_volatility', 0)
            
            if iv <= 0:
                logger.warning(f"Invalid IV for {symbol}: {iv}")
                return False
            
            # Store in database
            details = atm_option.get('details', {})
            success = self.iv_db.store_iv(
                symbol=symbol,
                iv=iv,
                date=datetime.now().date(),
                expiration_date=best_expiration,
                strike=details.get('strike_price'),
                option_type=option_type
            )
            
            if success:
                logger.info(f"Stored IV for {symbol}: {iv:.2%} (expiration: {best_expiration})")
            
            return success
            
        except Exception as e:
            logger.error(f"Error collecting IV for {symbol}: {e}")
            return False
    
    def collect_all_tickers_iv(self) -> Dict[str, bool]:
        """
        Collect IV for all configured tickers
        
        Returns:
            Dictionary mapping symbol -> success status
        """
        results = {}
        
        for symbol in Config.TICKERS:
            logger.info(f"Collecting IV for {symbol}...")
            success = self.collect_and_store_iv(symbol)
            results[symbol] = success
        
        return results
    
    def get_iv_rank(
        self,
        symbol: str,
        current_iv: Optional[float] = None,
        lookback_days: Optional[int] = None
    ) -> Optional[float]:
        """
        Calculate IV Rank for a symbol
        
        Args:
            symbol: Stock symbol
            current_iv: Current IV (fetches from database if None)
            lookback_days: Lookback period (uses default if None)
            
        Returns:
            IV Rank (0-100) or None
        """
        # Get current IV if not provided
        if current_iv is None:
            current_iv = self.iv_db.get_latest_iv(symbol)
            if current_iv is None:
                logger.warning(f"No IV data found for {symbol}")
                return None
        
        # Get IV history
        lookback = lookback_days or self.lookback_days
        iv_history = self.iv_db.get_iv_history(symbol, lookback_days=lookback)
        
        if not iv_history or len(iv_history) < 2:
            logger.warning(f"Insufficient IV history for {symbol} (need at least 2 data points)")
            return None
        
        # Calculate IV Rank
        iv_rank = self.iv_calculator.calculate_iv_rank(symbol, current_iv, iv_history)
        
        return iv_rank
    
    def get_iv_percentile(
        self,
        symbol: str,
        current_iv: Optional[float] = None,
        lookback_days: Optional[int] = None
    ) -> Optional[float]:
        """
        Calculate IV Percentile for a symbol
        
        Args:
            symbol: Stock symbol
            current_iv: Current IV (fetches from database if None)
            lookback_days: Lookback period (uses default if None)
            
        Returns:
            IV Percentile (0-100) or None
        """
        # Get current IV if not provided
        if current_iv is None:
            current_iv = self.iv_db.get_latest_iv(symbol)
            if current_iv is None:
                logger.warning(f"No IV data found for {symbol}")
                return None
        
        # Get IV history
        lookback = lookback_days or self.lookback_days
        iv_history = self.iv_db.get_iv_history(symbol, lookback_days=lookback)
        
        if not iv_history:
            logger.warning(f"No IV history for {symbol}")
            return None
        
        # Calculate IV Percentile
        iv_percentile = self.iv_calculator.calculate_iv_percentile(symbol, current_iv, iv_history)
        
        return iv_percentile
    
    def get_iv_metrics(
        self,
        symbol: str,
        lookback_days: Optional[int] = None
    ) -> Dict[str, Optional[float]]:
        """
        Get comprehensive IV metrics for a symbol
        
        Args:
            symbol: Stock symbol
            lookback_days: Lookback period (uses default if None)
            
        Returns:
            Dictionary with:
            - current_iv: Current IV
            - iv_rank: IV Rank (0-100)
            - iv_percentile: IV Percentile (0-100)
            - min_iv: Minimum IV in lookback period
            - max_iv: Maximum IV in lookback period
            - avg_iv: Average IV in lookback period
        """
        lookback = lookback_days or self.lookback_days
        
        # Get current IV
        current_iv = self.iv_db.get_latest_iv(symbol)
        
        # Get IV history
        iv_history = self.iv_db.get_iv_history(symbol, lookback_days=lookback)
        
        if not iv_history:
            return {
                'current_iv': None,
                'iv_rank': None,
                'iv_percentile': None,
                'min_iv': None,
                'max_iv': None,
                'avg_iv': None
            }
        
        # Calculate metrics
        iv_rank = self.get_iv_rank(symbol, current_iv, lookback) if current_iv else None
        iv_percentile = self.get_iv_percentile(symbol, current_iv, lookback) if current_iv else None
        
        return {
            'current_iv': current_iv,
            'iv_rank': iv_rank,
            'iv_percentile': iv_percentile,
            'min_iv': min(iv_history) if iv_history else None,
            'max_iv': max(iv_history) if iv_history else None,
            'avg_iv': sum(iv_history) / len(iv_history) if iv_history else None,
            'data_points': len(iv_history)
        }
    
    def get_all_tickers_iv_metrics(self) -> Dict[str, Dict[str, Optional[float]]]:
        """
        Get IV metrics for all configured tickers
        
        Returns:
            Dictionary mapping symbol -> IV metrics
        """
        results = {}
        
        for symbol in Config.TICKERS:
            metrics = self.get_iv_metrics(symbol)
            results[symbol] = metrics
        
        return results
    
    def update_iv_history_from_feed(self, symbol: str) -> bool:
        """
        Update IV history by collecting from options feed
        
        This is a convenience method that combines collection and storage
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if successful
        """
        return self.collect_and_store_iv(symbol)

