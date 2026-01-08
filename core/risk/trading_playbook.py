"""
Trading Playbook Manager
Implements Architect 3's Scalp vs Swing playbook separation

Key Insight: "Scalp and Swing are different businesses"
"""
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, time
import pytz

logger = logging.getLogger(__name__)

ET = pytz.timezone('America/New_York')


class PlaybookMode(Enum):
    """Trading playbook modes"""
    SCALP = "scalp"   # 0-3 DTE aggressive
    SWING = "swing"   # 7-21 DTE patient


@dataclass
class ScalpPlaybook:
    """
    Scalp Playbook (0-3 DTE)
    
    Characteristics:
    - Smaller position sizes
    - Tighter stops
    - Faster profit-taking
    - Mandatory time exits
    - Stricter spread/OI rules
    """
    # Position sizing (% of portfolio)
    max_position_pct: float = 0.05  # 5% max (smaller than swing)
    
    # Stop loss (tighter)
    stop_loss_pct: float = 0.15  # 15% stop (not 20%)
    
    # Profit taking (faster)
    tp1_pct: float = 0.25  # +25% (not 40%)
    tp1_exit_pct: float = 0.50  # Exit 50%
    tp2_pct: float = 0.40  # +40%
    tp2_exit_pct: float = 0.30  # Exit 30%
    tp3_pct: float = 0.60  # +60% (exit remaining)
    
    # Time-based mandatory exits
    mandatory_exit_minutes_before_close: int = 120  # 2 hours before close
    exit_if_flat_after_minutes: int = 60  # Exit if no movement after 1 hour
    
    # Stricter liquidity requirements
    min_spread_pct: float = 0.03  # Max 3% spread
    min_volume: int = 500
    min_open_interest: int = 1000
    
    # DTE constraints
    min_dte: int = 0
    max_dte: int = 3
    
    # Gamma protection
    max_gamma_per_contract: float = 0.30  # Lower gamma tolerance


@dataclass
class SwingPlaybook:
    """
    Swing Playbook (7-21 DTE)
    
    Characteristics:
    - Larger position sizes (more time to be right)
    - Standard stops
    - Patient profit targets
    - Theta budget management
    - Roll rules for expiring positions
    """
    # Position sizing (% of portfolio)
    max_position_pct: float = 0.10  # 10% max
    
    # Stop loss (standard)
    stop_loss_pct: float = 0.20  # 20% stop
    
    # Profit taking (patient)
    tp1_pct: float = 0.40  # +40%
    tp1_exit_pct: float = 0.50
    tp2_pct: float = 0.60  # +60%
    tp2_exit_pct: float = 0.20
    tp3_pct: float = 1.00  # +100%
    tp3_exit_pct: float = 0.10
    tp4_pct: float = 1.50  # +150%
    tp4_exit_pct: float = 0.10
    tp5_pct: float = 2.00  # +200%
    tp5_exit_pct: float = 0.10
    
    # Time-based exits (less aggressive)
    mandatory_exit_dte: int = 3  # Must exit at 3 DTE if not profitable
    
    # Standard liquidity requirements
    min_spread_pct: float = 0.05  # Max 5% spread
    min_volume: int = 200
    min_open_interest: int = 500
    
    # DTE constraints
    min_dte: int = 7
    max_dte: int = 21
    
    # Theta budget
    max_daily_theta_burn_pct: float = 0.005  # 0.5% of portfolio per day
    
    # Roll rules
    roll_at_dte: int = 5  # Consider rolling at 5 DTE
    roll_if_profit_below_pct: float = 0.10  # Roll if profit < 10%
    
    # Gamma tolerance (higher for swing)
    max_gamma_per_contract: float = 0.50


class PlaybookManager:
    """
    Manages trading playbooks and determines which rules to apply
    """
    
    def __init__(self):
        self.scalp = ScalpPlaybook()
        self.swing = SwingPlaybook()
        logger.info("PlaybookManager initialized with Scalp and Swing playbooks")
    
    def get_playbook_for_dte(self, dte: int) -> Tuple[PlaybookMode, object]:
        """
        Get appropriate playbook based on DTE
        
        Args:
            dte: Days to expiration
            
        Returns:
            (mode, playbook)
        """
        if dte <= 3:
            return PlaybookMode.SCALP, self.scalp
        else:
            return PlaybookMode.SWING, self.swing
    
    def get_position_size_pct(self, dte: int) -> float:
        """Get max position size % based on DTE"""
        mode, playbook = self.get_playbook_for_dte(dte)
        return playbook.max_position_pct
    
    def get_stop_loss_pct(self, dte: int) -> float:
        """Get stop loss % based on DTE"""
        mode, playbook = self.get_playbook_for_dte(dte)
        return playbook.stop_loss_pct
    
    def get_profit_targets(self, dte: int) -> Dict:
        """Get profit targets based on DTE"""
        mode, playbook = self.get_playbook_for_dte(dte)
        
        if mode == PlaybookMode.SCALP:
            return {
                'tp1': (playbook.tp1_pct, playbook.tp1_exit_pct),
                'tp2': (playbook.tp2_pct, playbook.tp2_exit_pct),
                'tp3': (playbook.tp3_pct, 1.0),  # Exit remaining
            }
        else:
            return {
                'tp1': (playbook.tp1_pct, playbook.tp1_exit_pct),
                'tp2': (playbook.tp2_pct, playbook.tp2_exit_pct),
                'tp3': (playbook.tp3_pct, playbook.tp3_exit_pct),
                'tp4': (playbook.tp4_pct, playbook.tp4_exit_pct),
                'tp5': (playbook.tp5_pct, playbook.tp5_exit_pct),
            }
    
    def check_time_exit(self, dte: int, current_pnl_pct: float) -> Tuple[bool, str]:
        """
        Check if time-based exit is required
        
        Args:
            dte: Days to expiration
            current_pnl_pct: Current P&L as decimal
            
        Returns:
            (should_exit, reason)
        """
        mode, playbook = self.get_playbook_for_dte(dte)
        now_et = datetime.now(ET)
        current_time = now_et.time()
        
        if mode == PlaybookMode.SCALP:
            # Check time until market close
            market_close = time(16, 0)
            minutes_to_close = (
                (market_close.hour - current_time.hour) * 60 +
                (market_close.minute - current_time.minute)
            )
            
            # 0DTE: Exit 2 hours before close if profit < 10%
            if dte == 0 and minutes_to_close <= playbook.mandatory_exit_minutes_before_close:
                if current_pnl_pct < 0.10:
                    return True, f"0DTE TIME EXIT: {minutes_to_close} min to close, P&L {current_pnl_pct:.1%}"
            
            return False, ""
        
        else:  # Swing
            # Exit at 3 DTE if not profitable
            if dte <= playbook.mandatory_exit_dte and current_pnl_pct < 0.10:
                return True, f"SWING DTE EXIT: {dte} DTE with {current_pnl_pct:.1%} profit"
            
            return False, ""
    
    def check_theta_budget(
        self, 
        dte: int, 
        position_theta: float, 
        portfolio_value: float
    ) -> Tuple[bool, str]:
        """
        Check if position theta is within budget (swing only)
        
        Args:
            dte: Days to expiration
            position_theta: Daily theta burn in $
            portfolio_value: Total portfolio value
            
        Returns:
            (within_budget, reason)
        """
        mode, playbook = self.get_playbook_for_dte(dte)
        
        if mode == PlaybookMode.SWING:
            max_theta = portfolio_value * playbook.max_daily_theta_burn_pct
            
            if abs(position_theta) > max_theta:
                return False, f"THETA BUDGET: ${abs(position_theta):.0f}/day exceeds ${max_theta:.0f} limit"
        
        return True, ""
    
    def should_roll(self, dte: int, current_pnl_pct: float) -> Tuple[bool, str]:
        """
        Check if position should be rolled (swing only)
        
        Args:
            dte: Days to expiration
            current_pnl_pct: Current P&L as decimal
            
        Returns:
            (should_roll, reason)
        """
        mode, playbook = self.get_playbook_for_dte(dte)
        
        if mode == PlaybookMode.SWING:
            if dte <= playbook.roll_at_dte:
                if current_pnl_pct < playbook.roll_if_profit_below_pct:
                    return True, f"ROLL SIGNAL: {dte} DTE with {current_pnl_pct:.1%} profit"
        
        return False, ""
    
    def check_liquidity_requirements(
        self, 
        dte: int, 
        spread_pct: float, 
        volume: int, 
        open_interest: int
    ) -> Tuple[bool, str]:
        """
        Check if option meets liquidity requirements for playbook
        
        Args:
            dte: Days to expiration
            spread_pct: Bid-ask spread as % of ask
            volume: Option volume
            open_interest: Open interest
            
        Returns:
            (passes, reason)
        """
        mode, playbook = self.get_playbook_for_dte(dte)
        
        if spread_pct > playbook.min_spread_pct:
            return False, f"SPREAD REJECT ({mode.value}): {spread_pct:.1%} > {playbook.min_spread_pct:.1%}"
        
        if volume < playbook.min_volume:
            return False, f"VOLUME REJECT ({mode.value}): {volume} < {playbook.min_volume}"
        
        if open_interest < playbook.min_open_interest:
            return False, f"OI REJECT ({mode.value}): {open_interest} < {playbook.min_open_interest}"
        
        return True, f"Liquidity OK for {mode.value}"
    
    def get_gamma_limit(self, dte: int) -> float:
        """Get max gamma per contract based on DTE"""
        mode, playbook = self.get_playbook_for_dte(dte)
        return playbook.max_gamma_per_contract
    
    def get_playbook_summary(self, dte: int) -> Dict:
        """Get summary of active playbook"""
        mode, playbook = self.get_playbook_for_dte(dte)
        
        return {
            'mode': mode.value,
            'max_position_pct': playbook.max_position_pct,
            'stop_loss_pct': playbook.stop_loss_pct,
            'min_spread_pct': playbook.min_spread_pct,
            'min_volume': playbook.min_volume,
            'min_open_interest': playbook.min_open_interest,
            'max_gamma': playbook.max_gamma_per_contract,
        }


# Singleton instance
playbook_manager = PlaybookManager()

