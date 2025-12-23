"""
IV Regime Manager
Enforces IV Rank-based trading rules and position sizing
"""
import logging
from typing import Dict, Optional, Tuple
from services.iv_rank_service import IVRankService

logger = logging.getLogger(__name__)

class IVRegimeManager:
    """
    Manages IV Rank regimes and enforces trading rules
    
    IV Regimes:
    - Low IV (IV Rank < 20%): Avoid buying short-dated options
    - Normal (IV Rank 20-50%): Standard trading
    - High IV (IV Rank 50-80%): Favor premium selling or fast exits
    - Extreme IV (IV Rank > 80%): Reduce size or skip trades
    """
    
    # IV Regime thresholds
    LOW_IV_THRESHOLD = 20.0
    NORMAL_IV_THRESHOLD = 50.0
    HIGH_IV_THRESHOLD = 80.0
    
    def __init__(self, iv_rank_service: Optional[IVRankService] = None):
        """
        Initialize IV Regime Manager
        
        Args:
            iv_rank_service: IV Rank service (creates if None)
        """
        self.iv_rank_service = iv_rank_service or IVRankService()
    
    def get_iv_regime(self, symbol: str) -> Tuple[str, Optional[float]]:
        """
        Get IV regime for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Tuple of (regime_name, iv_rank) or ('unknown', None) if insufficient data
        """
        iv_rank = self.iv_rank_service.get_iv_rank(symbol)
        
        if iv_rank is None:
            return ('unknown', None)
        
        if iv_rank < self.LOW_IV_THRESHOLD:
            return ('low', iv_rank)
        elif iv_rank < self.NORMAL_IV_THRESHOLD:
            return ('normal', iv_rank)
        elif iv_rank < self.HIGH_IV_THRESHOLD:
            return ('high', iv_rank)
        else:
            return ('extreme', iv_rank)
    
    def can_trade_long_options(self, symbol: str) -> Tuple[bool, str]:
        """
        Check if long options trades are allowed
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Tuple of (allowed, reason)
        """
        regime, iv_rank = self.get_iv_regime(symbol)
        
        if regime == 'unknown':
            # If no IV Rank data, allow but warn
            return (True, "IV Rank data unavailable - trading allowed")
        
        if regime == 'extreme':
            # Block long calls in extreme IV (IV crush risk)
            return (False, f"IV Rank {iv_rank:.1f}% is extreme (>80%) - blocking long options to avoid IV crush")
        
        if regime == 'low':
            # Warn but allow in low IV (may be good for long options)
            return (True, f"IV Rank {iv_rank:.1f}% is low (<20%) - long options may have limited upside")
        
        # Normal and high IV: allow
        return (True, f"IV Rank {iv_rank:.1f}% is {regime} - trading allowed")
    
    def can_trade_short_premium(self, symbol: str) -> Tuple[bool, str]:
        """
        Check if short premium trades are allowed
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Tuple of (allowed, reason)
        """
        regime, iv_rank = self.get_iv_regime(symbol)
        
        if regime == 'unknown':
            return (True, "IV Rank data unavailable - trading allowed")
        
        if regime == 'low':
            # Block short premium in low IV (low premium, high risk)
            return (False, f"IV Rank {iv_rank:.1f}% is low (<20%) - blocking short premium (low premium, high risk)")
        
        if regime in ['high', 'extreme']:
            # Favor short premium in high IV
            return (True, f"IV Rank {iv_rank:.1f}% is {regime} - favorable for short premium")
        
        # Normal IV: allow
        return (True, f"IV Rank {iv_rank:.1f}% is normal - trading allowed")
    
    def get_position_size_multiplier(self, symbol: str) -> float:
        """
        Get position size multiplier based on IV Rank
        
        Reduces size in extreme IV to limit blow-up risk
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Multiplier (0.0 to 1.0)
        """
        regime, iv_rank = self.get_iv_regime(symbol)
        
        if regime == 'unknown':
            return 1.0  # No adjustment if no data
        
        if regime == 'extreme':
            # Reduce size by 40% in extreme IV
            return 0.6
        
        if regime == 'high':
            # Reduce size by 20% in high IV
            return 0.8
        
        # Normal and low IV: full size
        return 1.0
    
    def should_favor_fast_exit(self, symbol: str) -> bool:
        """
        Check if fast exits should be favored (high IV regimes)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if fast exits should be favored
        """
        regime, _ = self.get_iv_regime(symbol)
        
        # Favor fast exits in high/extreme IV to capture premium before IV crush
        return regime in ['high', 'extreme']
    
    def get_iv_risk_adjustment(self, symbol: str) -> Dict[str, any]:
        """
        Get comprehensive IV risk adjustments
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with IV risk adjustments
        """
        regime, iv_rank = self.get_iv_regime(symbol)
        current_iv = self.iv_rank_service.iv_db.get_latest_iv(symbol)
        
        can_long, long_reason = self.can_trade_long_options(symbol)
        can_short, short_reason = self.can_trade_short_premium(symbol)
        
        return {
            'regime': regime,
            'iv_rank': iv_rank,
            'current_iv': current_iv,
            'can_trade_long': can_long,
            'can_trade_long_reason': long_reason,
            'can_trade_short_premium': can_short,
            'can_trade_short_reason': short_reason,
            'position_size_multiplier': self.get_position_size_multiplier(symbol),
            'favor_fast_exit': self.should_favor_fast_exit(symbol)
        }

