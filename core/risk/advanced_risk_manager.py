"""
Advanced Risk Manager
Guardrails, circuit breakers, and risk controls
Integrated with IV Regime Manager and UVaR for comprehensive risk management
"""
import logging
from typing import Dict, Optional, List, Tuple
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
        max_spread_pct: float = 0.05,  # 5%
        use_iv_regimes: bool = True
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
            use_iv_regimes: Enable IV regime-based trading rules
        """
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_loss_streak = max_loss_streak
        self.max_iv_rank = max_iv_rank
        self.max_vix = max_vix
        self.max_spread_pct = max_spread_pct
        self.use_iv_regimes = use_iv_regimes
        
        # Gap Risk Monitor (lazy import)
        self.gap_risk_monitor = None
        self.use_gap_risk = True
        try:
            from core.risk.gap_risk_monitor import GapRiskMonitor
            self.gap_risk_monitor = GapRiskMonitor()
        except Exception as e:
            logger.warning(f"Could not initialize Gap Risk Monitor: {e}")
            self.use_gap_risk = False
        
        # IV Regime Manager (lazy import to avoid circular dependencies)
        self.iv_regime_manager = None
        if use_iv_regimes:
            try:
                from core.risk.iv_regime_manager import IVRegimeManager
                self.iv_regime_manager = IVRegimeManager()
            except Exception as e:
                logger.warning(f"Could not initialize IV Regime Manager: {e}")
                self.use_iv_regimes = False
        
        # UVaR Calculator (lazy import, requires Alpaca client)
        self.uvar_calculator = None
        self.max_uvar_pct = 5.0  # Default 5% UVaR threshold
        self.use_uvar = False  # Will be enabled when Alpaca client is provided
        
        # Tracking
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        self.loss_streak = 0
        self.peak_balance = initial_balance
        self.kill_switch_active = False
        
        # Trade history
        self.trade_history: List[Dict] = []
    
    def enable_uvar(self, alpaca_client, max_uvar_pct: float = 5.0):
        """
        Enable UVaR checking (requires Alpaca client)
        
        Args:
            alpaca_client: Alpaca API client
            max_uvar_pct: Maximum UVaR as percentage of portfolio (default: 5%)
        """
        try:
            from core.risk.uvar_calculator import UVaRCalculator
            self.uvar_calculator = UVaRCalculator(alpaca_client=alpaca_client)
            self.max_uvar_pct = max_uvar_pct
            self.use_uvar = True
            logger.info(f"UVaR enabled with {max_uvar_pct}% threshold")
        except Exception as e:
            logger.warning(f"Could not enable UVaR: {e}")
            self.use_uvar = False
        
    def check_trade_allowed(
        self,
        symbol: str,
        qty: float,
        price: float,
        side: str,
        iv_rank: Optional[float] = None,
        vix: Optional[float] = None,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
        current_positions: Optional[List[Dict]] = None
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
        
        # Gap Risk check (FIRST - before other checks)
        if self.use_gap_risk and self.gap_risk_monitor:
            can_trade, gap_reason = self.gap_risk_monitor.can_trade(symbol)
            if not can_trade:
                return False, gap_reason, RiskLevel.BLOCKED
            
            # Check if force exit is required
            if self.gap_risk_monitor.should_force_exit(symbol):
                return False, f"Gap risk: {gap_reason} - force exit required", RiskLevel.BLOCKED
        
        # Check IV Rank (basic threshold)
        if iv_rank and iv_rank > self.max_iv_rank:
            return False, f"IV Rank too high ({iv_rank:.1f}%)", RiskLevel.BLOCKED
        
        # IV Regime-based checks (if enabled)
        if self.use_iv_regimes and self.iv_regime_manager:
            # Check IV regime rules
            # For long options (buying calls/puts)
            if side.lower() in ['buy', 'long']:
                can_trade, reason = self.iv_regime_manager.can_trade_long_options(symbol)
                if not can_trade:
                    return False, reason, RiskLevel.BLOCKED
            
            # For short premium (selling options)
            elif side.lower() in ['sell', 'short']:
                can_trade, reason = self.iv_regime_manager.can_trade_short_premium(symbol)
                if not can_trade:
                    return False, reason, RiskLevel.BLOCKED
        
        # Check VIX
        if vix and vix > self.max_vix:
            return False, f"VIX too high ({vix:.1f})", RiskLevel.BLOCKED
        
        # Check spread
        if bid and ask:
            spread_pct = (ask - bid) / bid
            if spread_pct > self.max_spread_pct:
                return False, f"Spread too wide ({spread_pct:.2%})", RiskLevel.BLOCKED
        
        # UVaR check (if enabled and positions provided)
        if self.use_uvar and self.uvar_calculator and current_positions is not None:
            # Create new position dict for incremental UVaR check
            new_position = {
                'symbol': symbol,
                'qty': qty if side.lower() in ['buy', 'long'] else -qty,
                'entry_price': price,
                'current_price': price
            }
            
            # Check incremental UVaR
            incremental = self.uvar_calculator.calculate_incremental_uvar(
                current_positions,
                new_position,
                horizon_days=1
            )
            
            # Check if adding this position would breach UVaR
            if incremental['uvar_after_pct'] > self.max_uvar_pct:
                return (
                    False,
                    f"UVaR breach: {incremental['uvar_after_pct']:.2f}% > {self.max_uvar_pct}% threshold",
                    RiskLevel.BLOCKED
                )
            
            # Soft breach warning (80% of threshold)
            if incremental['uvar_after_pct'] > self.max_uvar_pct * 0.8:
                logger.warning(
                    f"UVaR approaching limit: {incremental['uvar_after_pct']:.2f}% "
                    f"(threshold: {self.max_uvar_pct}%)"
                )
        
        # All checks passed
        return True, "Trade allowed", RiskLevel.SAFE
    
    def get_iv_adjusted_position_size(
        self,
        symbol: str,
        base_size: float
    ) -> float:
        """
        Get IV-adjusted position size
        
        Reduces position size in extreme IV regimes
        
        Args:
            symbol: Stock symbol
            base_size: Base position size
            
        Returns:
            Adjusted position size
        """
        if self.use_iv_regimes and self.iv_regime_manager:
            multiplier = self.iv_regime_manager.get_position_size_multiplier(symbol)
            return base_size * multiplier
        
        return base_size
    
    def get_gap_risk_adjusted_position_size(
        self,
        symbol: str,
        base_size: float
    ) -> float:
        """
        Get gap risk-adjusted position size
        
        Reduces position size before earnings/macro events
        
        Args:
            symbol: Stock symbol
            base_size: Base position size
            
        Returns:
            Adjusted position size
        """
        if self.use_gap_risk and self.gap_risk_monitor:
            multiplier = self.gap_risk_monitor.get_position_size_multiplier(symbol)
            return base_size * multiplier
        
        return base_size
    
    def get_final_position_size(
        self,
        symbol: str,
        base_size: float
    ) -> float:
        """
        Get final position size after all adjustments
        
        Applies gap risk, then IV regime adjustments
        
        Args:
            symbol: Stock symbol
            base_size: Base position size
            
        Returns:
            Final adjusted position size
        """
        # Apply gap risk first
        size = self.get_gap_risk_adjusted_position_size(symbol, base_size)
        
        # Then apply IV regime
        size = self.get_iv_adjusted_position_size(symbol, size)
        
        return size
    
    def should_force_exit_position(
        self,
        symbol: str
    ) -> bool:
        """
        Check if position should be forced to exit (earnings today, etc.)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if position should be forced to exit
        """
        if self.use_gap_risk and self.gap_risk_monitor:
            return self.gap_risk_monitor.should_force_exit(symbol)
        
        return False
    
    def should_favor_fast_exit(self, symbol: str) -> bool:
        """
        Check if fast exits should be favored (high IV regimes)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            True if fast exits should be favored
        """
        if self.use_iv_regimes and self.iv_regime_manager:
            return self.iv_regime_manager.should_favor_fast_exit(symbol)
        
        return False
    
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
    
    def get_gap_risk_status(self, symbol: str) -> Dict:
        """
        Get gap risk status for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with gap risk details
        """
        if self.use_gap_risk and self.gap_risk_monitor:
            risk_level, reason, details = self.gap_risk_monitor.get_gap_risk(symbol)
            return {
                'risk_level': risk_level.value,
                'reason': reason,
                **details
            }
        
        return {
            'risk_level': 'none',
            'reason': 'Gap risk monitor not enabled',
            'position_size_multiplier': 1.0,
            'block_new_trades': False,
            'force_exit': False
        }
    
    def get_risk_status(self, current_positions: Optional[List[Dict]] = None) -> Dict:
        """
        Get current risk status
        
        Args:
            current_positions: Optional list of current positions for UVaR calculation
            
        Returns:
            Dictionary with risk status including UVaR if enabled
        """
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
        
        status = {
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
        
        # Add UVaR if enabled and positions provided
        if self.use_uvar and self.uvar_calculator and current_positions:
            try:
                uvar_result = self.uvar_calculator.calculate_uvar(current_positions, horizon_days=1)
                status['uvar'] = uvar_result['uvar']
                status['uvar_pct'] = uvar_result['uvar_pct']
                status['uvar_breach'] = uvar_result['uvar_pct'] > self.max_uvar_pct
            except Exception as e:
                logger.warning(f"Could not calculate UVaR: {e}")
        
        return status
    
    def _reset_daily_if_needed(self):
        """Reset daily tracking if new day"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = today
            logger.info("Daily risk tracking reset")

