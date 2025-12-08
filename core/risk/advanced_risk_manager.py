"""
Advanced Risk Manager
Guardrails, circuit breakers, and risk controls
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Risk levels"""
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"
    BLOCKED = "blocked"

class AdvancedRiskManager:
    """Advanced risk management with guardrails"""
    
    def __init__(
        self,
        initial_balance: float,
        daily_loss_limit_pct: float = 0.02,  # 2%
        max_drawdown_pct: float = 0.10,  # 10%
        max_loss_streak: int = 3,
        max_iv_rank: float = 95.0,
        max_vix: float = 32.0,
        max_spread_pct: float = 0.05  # 5%
    ):
        """
        Initialize risk manager
        
        Args:
            initial_balance: Starting balance
            daily_loss_limit_pct: Maximum daily loss percentage
            max_drawdown_pct: Maximum drawdown percentage
            max_loss_streak: Maximum consecutive losses before shutdown
            max_iv_rank: Maximum IV Rank to allow trading
            max_vix: Maximum VIX level
            max_spread_pct: Maximum bid-ask spread percentage
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_loss_streak = max_loss_streak
        self.max_iv_rank = max_iv_rank
        self.max_vix = max_vix
        self.max_spread_pct = max_spread_pct
        
        # Tracking
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        self.loss_streak = 0
        self.peak_balance = initial_balance
        self.kill_switch_active = False
        
        # Trade history
        self.trade_history: List[Dict] = []
        
    def check_trade_allowed(
        self,
        symbol: str,
        qty: float,
        price: float,
        side: str,
        iv_rank: Optional[float] = None,
        vix: Optional[float] = None,
        bid: Optional[float] = None,
        ask: Optional[float] = None
    ) -> tuple[bool, str, RiskLevel]:
        """
        Check if trade is allowed
        
        Returns:
            (allowed, reason, risk_level)
        """
        # Reset daily tracking if new day
        self._reset_daily_if_needed()
        
        # Check kill switch
        if self.kill_switch_active:
            return False, "Kill switch is active", RiskLevel.BLOCKED
        
        # Check daily loss limit
        daily_loss_pct = abs(self.daily_pnl) / self.current_balance if self.current_balance > 0 else 0
        if daily_loss_pct >= self.daily_loss_limit_pct:
            return False, f"Daily loss limit reached ({daily_loss_pct:.2%})", RiskLevel.BLOCKED
        
        # Check drawdown
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        if drawdown >= self.max_drawdown_pct:
            return False, f"Max drawdown reached ({drawdown:.2%})", RiskLevel.BLOCKED
        
        # Check loss streak
        if self.loss_streak >= self.max_loss_streak:
            return False, f"Max loss streak reached ({self.loss_streak})", RiskLevel.BLOCKED
        
        # Check IV Rank
        if iv_rank and iv_rank > self.max_iv_rank:
            return False, f"IV Rank too high ({iv_rank:.1f}%)", RiskLevel.BLOCKED
        
        # Check VIX
        if vix and vix > self.max_vix:
            return False, f"VIX too high ({vix:.1f})", RiskLevel.BLOCKED
        
        # Check spread
        if bid and ask:
            spread_pct = (ask - bid) / bid
            if spread_pct > self.max_spread_pct:
                return False, f"Spread too wide ({spread_pct:.2%})", RiskLevel.BLOCKED
        
        # All checks passed
        return True, "Trade allowed", RiskLevel.SAFE
    
    def record_trade(
        self,
        symbol: str,
        qty: float,
        entry_price: float,
        exit_price: Optional[float],
        pnl: float,
        side: str
    ):
        """Record a completed trade"""
        trade = {
            'symbol': symbol,
            'qty': qty,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'side': side,
            'timestamp': datetime.now().isoformat()
        }
        
        self.trade_history.append(trade)
        
        # Update daily P&L
        self.daily_pnl += pnl
        
        # Update balance
        self.current_balance += pnl
        
        # Update peak balance
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        # Update loss streak
        if pnl < 0:
            self.loss_streak += 1
        else:
            self.loss_streak = 0
        
        logger.info(f"Trade recorded: {symbol} P&L=${pnl:.2f}, Daily P&L=${self.daily_pnl:.2f}")
    
    def update_balance(self, new_balance: float):
        """Update current balance"""
        self.current_balance = new_balance
        
        if new_balance > self.peak_balance:
            self.peak_balance = new_balance
    
    def activate_kill_switch(self, reason: str = "Manual activation"):
        """Activate kill switch"""
        self.kill_switch_active = True
        logger.warning(f"Kill switch activated: {reason}")
    
    def deactivate_kill_switch(self):
        """Deactivate kill switch"""
        self.kill_switch_active = False
        logger.info("Kill switch deactivated")
    
    def get_risk_status(self) -> Dict:
        """Get current risk status"""
        self._reset_daily_if_needed()
        
        daily_loss_pct = abs(self.daily_pnl) / self.current_balance if self.current_balance > 0 else 0
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        
        risk_level = RiskLevel.SAFE
        if self.kill_switch_active:
            risk_level = RiskLevel.BLOCKED
        elif daily_loss_pct >= self.daily_loss_limit_pct * 0.8 or drawdown >= self.max_drawdown_pct * 0.8:
            risk_level = RiskLevel.DANGER
        elif daily_loss_pct >= self.daily_loss_limit_pct * 0.5 or drawdown >= self.max_drawdown_pct * 0.5:
            risk_level = RiskLevel.WARNING
        
        return {
            'risk_level': risk_level.value,
            'kill_switch_active': self.kill_switch_active,
            'daily_pnl': self.daily_pnl,
            'daily_loss_pct': daily_loss_pct,
            'current_balance': self.current_balance,
            'peak_balance': self.peak_balance,
            'drawdown': drawdown,
            'loss_streak': self.loss_streak,
            'total_trades': len(self.trade_history),
            'winning_trades': sum(1 for t in self.trade_history if t['pnl'] > 0),
            'losing_trades': sum(1 for t in self.trade_history if t['pnl'] < 0)
        }
    
    def _reset_daily_if_needed(self):
        """Reset daily tracking if new day"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = today
            logger.info("Daily risk tracking reset")

