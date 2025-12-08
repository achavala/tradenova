"""
IV Rank and Percentile Calculator
Calculates Implied Volatility Rank and Percentile
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class IVCalculator:
    """Calculate IV Rank and Percentile"""
    
    def __init__(self, lookback_days: int = 252):
        """
        Initialize IV calculator
        
        Args:
            lookback_days: Number of days to look back for IV history
        """
        self.lookback_days = lookback_days
        self.iv_history: Dict[str, List[float]] = {}  # symbol -> [iv values]
    
    def calculate_iv_rank(
        self, 
        symbol: str, 
        current_iv: float,
        iv_history: Optional[List[float]] = None
    ) -> float:
        """
        Calculate IV Rank (0-100)
        
        IV Rank = (Current IV - 52-week low IV) / (52-week high IV - 52-week low IV) * 100
        
        Args:
            symbol: Underlying symbol
            current_iv: Current implied volatility
            iv_history: Optional IV history (if None, uses stored history)
            
        Returns:
            IV Rank (0-100)
        """
        if iv_history is None:
            iv_history = self.iv_history.get(symbol, [])
        
        if not iv_history or len(iv_history) < 2:
            # Not enough history, return 50 (neutral)
            return 50.0
        
        iv_min = min(iv_history)
        iv_max = max(iv_history)
        
        if iv_max == iv_min:
            return 50.0
        
        iv_rank = ((current_iv - iv_min) / (iv_max - iv_min)) * 100
        
        # Clamp to 0-100
        return max(0.0, min(100.0, iv_rank))
    
    def calculate_iv_percentile(
        self,
        symbol: str,
        current_iv: float,
        iv_history: Optional[List[float]] = None
    ) -> float:
        """
        Calculate IV Percentile (0-100)
        
        IV Percentile = Percentage of days where IV was lower than current IV
        
        Args:
            symbol: Underlying symbol
            current_iv: Current implied volatility
            iv_history: Optional IV history
            
        Returns:
            IV Percentile (0-100)
        """
        if iv_history is None:
            iv_history = self.iv_history.get(symbol, [])
        
        if not iv_history:
            return 50.0
        
        # Count how many days had lower IV
        lower_count = sum(1 for iv in iv_history if iv < current_iv)
        
        iv_percentile = (lower_count / len(iv_history)) * 100
        
        return iv_percentile
    
    def update_iv_history(self, symbol: str, iv: float, date: Optional[datetime] = None):
        """
        Update IV history for a symbol
        
        Args:
            symbol: Underlying symbol
            iv: Implied volatility value
            date: Optional date (defaults to today)
        """
        if symbol not in self.iv_history:
            self.iv_history[symbol] = []
        
        self.iv_history[symbol].append(iv)
        
        # Keep only last N days
        if len(self.iv_history[symbol]) > self.lookback_days:
            self.iv_history[symbol] = self.iv_history[symbol][-self.lookback_days:]
    
    def get_iv_metrics(
        self,
        symbol: str,
        current_iv: float
    ) -> Dict:
        """
        Get comprehensive IV metrics
        
        Args:
            symbol: Underlying symbol
            current_iv: Current implied volatility
            
        Returns:
            Dictionary with IV rank, percentile, and statistics
        """
        iv_history = self.iv_history.get(symbol, [])
        
        if not iv_history:
            return {
                'iv_rank': 50.0,
                'iv_percentile': 50.0,
                'iv_min': current_iv,
                'iv_max': current_iv,
                'iv_mean': current_iv,
                'iv_std': 0.0,
                'data_points': 0
            }
        
        iv_rank = self.calculate_iv_rank(symbol, current_iv, iv_history)
        iv_percentile = self.calculate_iv_percentile(symbol, current_iv, iv_history)
        
        return {
            'iv_rank': iv_rank,
            'iv_percentile': iv_percentile,
            'iv_min': min(iv_history),
            'iv_max': max(iv_history),
            'iv_mean': np.mean(iv_history),
            'iv_std': np.std(iv_history),
            'data_points': len(iv_history),
            'current_iv': current_iv
        }

