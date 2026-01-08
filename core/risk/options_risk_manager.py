"""
Options Risk Manager
Implements Phases B-E: Theta/DTE Governance, Greeks Control, IV Enforcement, Execution Optimization
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time
from dataclasses import dataclass
import pytz

from config import Config

logger = logging.getLogger(__name__)

ET = pytz.timezone('America/New_York')


@dataclass
class PositionGreeks:
    """Greeks for a single position"""
    symbol: str
    delta: float
    gamma: float
    theta: float
    vega: float
    qty: int
    dte: int
    iv: float
    underlying_price: float


@dataclass
class PortfolioGreeks:
    """Aggregated portfolio Greeks"""
    total_delta: float
    total_gamma: float
    total_theta: float
    total_vega: float
    position_count: int
    
    def is_within_limits(self) -> Tuple[bool, List[str]]:
        """Check if portfolio Greeks are within configured limits"""
        violations = []
        
        if abs(self.total_delta) > Config.MAX_PORTFOLIO_DELTA:
            violations.append(f"Delta {self.total_delta:.0f} exceeds limit {Config.MAX_PORTFOLIO_DELTA}")
        
        if abs(self.total_gamma) > Config.MAX_PORTFOLIO_GAMMA:
            violations.append(f"Gamma {self.total_gamma:.1f} exceeds limit {Config.MAX_PORTFOLIO_GAMMA}")
        
        if self.total_theta < Config.MAX_PORTFOLIO_THETA:
            violations.append(f"Theta {self.total_theta:.0f} exceeds decay limit {Config.MAX_PORTFOLIO_THETA}")
        
        if abs(self.total_vega) > Config.MAX_PORTFOLIO_VEGA:
            violations.append(f"Vega {self.total_vega:.1f} exceeds limit {Config.MAX_PORTFOLIO_VEGA}")
        
        return len(violations) == 0, violations


class OptionsRiskManager:
    """
    Comprehensive options risk management implementing:
    - Phase B: Theta + DTE Governance
    - Phase C: Greeks & Gamma Control
    - Phase D: IV Enforcement
    - Phase E: Execution Optimization
    """
    
    def __init__(self):
        """Initialize options risk manager"""
        self.position_greeks: Dict[str, PositionGreeks] = {}
        self.portfolio_greeks = PortfolioGreeks(0, 0, 0, 0, 0)
        self.daily_theta_burn = 0.0
        logger.info("OptionsRiskManager initialized with all phases enabled")
    
    # ========== PHASE B: THETA + DTE GOVERNANCE ==========
    
    def check_dte_exit(self, symbol: str, dte: int, unrealized_pnl_pct: float) -> Tuple[bool, str]:
        """
        Phase B: Check if position should be force-exited based on DTE
        
        Args:
            symbol: Option symbol
            dte: Days to expiration
            unrealized_pnl_pct: Unrealized P&L as decimal (0.20 = 20%)
            
        Returns:
            (should_exit, reason)
        """
        for max_dte, min_profit in Config.DTE_EXIT_RULES:
            if dte <= max_dte:
                if unrealized_pnl_pct < min_profit:
                    reason = (f"DTE EXIT: {symbol} has {dte} DTE with {unrealized_pnl_pct:.1%} profit "
                              f"(need {min_profit:.0%}+ to hold)")
                    logger.warning(reason)
                    return True, reason
                else:
                    logger.debug(f"{symbol}: {dte} DTE with {unrealized_pnl_pct:.1%} profit - OK to hold")
                    return False, ""
        
        return False, ""
    
    def get_dte_position_size_multiplier(self, dte: int) -> float:
        """
        Phase B: Get position size multiplier based on DTE
        
        Args:
            dte: Days to expiration
            
        Returns:
            Multiplier (0.0 - 1.0)
        """
        for max_dte, multiplier in Config.DTE_POSITION_SIZE_MULTIPLIERS:
            if dte <= max_dte:
                logger.debug(f"DTE {dte}: Using {multiplier:.0%} position size")
                return multiplier
        return 1.0
    
    def check_theta_budget(self, additional_theta: float) -> Tuple[bool, str]:
        """
        Phase B: Check if additional theta exposure is within daily budget
        
        Args:
            additional_theta: Theta of new position (negative value)
            
        Returns:
            (allowed, reason)
        """
        # Theta is typically negative (time decay costs money)
        new_total = self.portfolio_greeks.total_theta + additional_theta
        
        if new_total < Config.MAX_PORTFOLIO_THETA:
            reason = (f"THETA BUDGET: Adding {additional_theta:.0f} would bring total theta to "
                     f"{new_total:.0f}, exceeding limit of {Config.MAX_PORTFOLIO_THETA}")
            logger.warning(reason)
            return False, reason
        
        return True, ""
    
    # ========== PHASE C: GREEKS & GAMMA CONTROL ==========
    
    def update_position_greeks(self, position: PositionGreeks):
        """Update Greeks for a single position"""
        self.position_greeks[position.symbol] = position
        self._recalculate_portfolio_greeks()
    
    def remove_position_greeks(self, symbol: str):
        """Remove position from Greeks tracking"""
        if symbol in self.position_greeks:
            del self.position_greeks[symbol]
            self._recalculate_portfolio_greeks()
    
    def _recalculate_portfolio_greeks(self):
        """Recalculate aggregate portfolio Greeks"""
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        
        for pos in self.position_greeks.values():
            # Scale by quantity (each contract = 100 shares)
            multiplier = pos.qty * 100
            total_delta += pos.delta * multiplier
            total_gamma += pos.gamma * multiplier
            total_theta += pos.theta * multiplier
            total_vega += pos.vega * multiplier
        
        self.portfolio_greeks = PortfolioGreeks(
            total_delta=total_delta,
            total_gamma=total_gamma,
            total_theta=total_theta,
            total_vega=total_vega,
            position_count=len(self.position_greeks)
        )
        
        logger.debug(f"Portfolio Greeks: Δ={total_delta:.0f}, Γ={total_gamma:.1f}, "
                    f"Θ={total_theta:.0f}, V={total_vega:.1f}")
    
    def check_greeks_limits(self, new_position: Optional[PositionGreeks] = None) -> Tuple[bool, List[str]]:
        """
        Phase C: Check if portfolio Greeks are within limits
        
        Args:
            new_position: Optional new position to check hypothetically
            
        Returns:
            (allowed, list_of_violations)
        """
        if new_position:
            # Simulate adding new position
            temp_greeks = PortfolioGreeks(
                total_delta=self.portfolio_greeks.total_delta + new_position.delta * new_position.qty * 100,
                total_gamma=self.portfolio_greeks.total_gamma + new_position.gamma * new_position.qty * 100,
                total_theta=self.portfolio_greeks.total_theta + new_position.theta * new_position.qty * 100,
                total_vega=self.portfolio_greeks.total_vega + new_position.vega * new_position.qty * 100,
                position_count=self.portfolio_greeks.position_count + 1
            )
            return temp_greeks.is_within_limits()
        
        return self.portfolio_greeks.is_within_limits()
    
    def check_position_gamma(self, gamma: float, qty: int) -> Tuple[bool, str]:
        """
        Phase C: Check if single position gamma is within limits
        
        Args:
            gamma: Position gamma per contract
            qty: Number of contracts
            
        Returns:
            (allowed, reason)
        """
        position_gamma = abs(gamma * qty * 100)
        
        if position_gamma > Config.MAX_POSITION_GAMMA:
            reason = f"GAMMA LIMIT: Position gamma {position_gamma:.1f} exceeds limit {Config.MAX_POSITION_GAMMA}"
            logger.warning(reason)
            return False, reason
        
        return True, ""
    
    # ========== PHASE D: IV ENFORCEMENT & STRIKE SELECTION ==========
    
    def check_iv_rank_entry(self, symbol: str, iv_rank: float) -> Tuple[bool, str]:
        """
        Phase D: Check if IV Rank allows entry (hard gate)
        
        Args:
            symbol: Underlying symbol
            iv_rank: IV Rank as percentage (0-100)
            
        Returns:
            (allowed, reason)
        """
        if iv_rank > Config.MAX_IV_RANK_FOR_ENTRY:
            reason = (f"IV RANK GATE: {symbol} IV Rank {iv_rank:.1f}% exceeds max {Config.MAX_IV_RANK_FOR_ENTRY}% "
                     f"(premium too expensive)")
            logger.warning(reason)
            return False, reason
        
        if iv_rank < Config.MIN_IV_RANK_FOR_ENTRY:
            reason = (f"IV RANK GATE: {symbol} IV Rank {iv_rank:.1f}% below min {Config.MIN_IV_RANK_FOR_ENTRY}% "
                     f"(insufficient volatility)")
            logger.info(reason)
            return False, reason
        
        logger.debug(f"{symbol}: IV Rank {iv_rank:.1f}% within acceptable range")
        return True, ""
    
    def get_target_delta_range(self, confidence: float) -> Tuple[float, float]:
        """
        Phase D: Get target delta range based on signal confidence
        
        Args:
            confidence: Signal confidence (0.0 - 1.0)
            
        Returns:
            (min_delta, max_delta) tuple
        """
        for min_conf, max_conf, delta_range in Config.DELTA_SELECTION_RULES:
            if min_conf <= confidence < max_conf:
                logger.debug(f"Confidence {confidence:.1%}: Target delta range {delta_range}")
                return delta_range
        
        return Config.DEFAULT_TARGET_DELTA
    
    def select_strike_by_delta(
        self, 
        options_chain: List[Dict], 
        option_type: str,
        target_delta_range: Tuple[float, float]
    ) -> Optional[Dict]:
        """
        Phase D: Select strike based on target delta range
        
        Args:
            options_chain: List of option contracts with Greeks
            option_type: 'call' or 'put'
            target_delta_range: (min_delta, max_delta)
            
        Returns:
            Selected option contract or None
        """
        min_delta, max_delta = target_delta_range
        candidates = []
        
        for contract in options_chain:
            # Get delta from contract (handle different field names)
            delta = contract.get('delta') or contract.get('greeks', {}).get('delta')
            if delta is None:
                continue
            
            delta = abs(float(delta))  # Use absolute value
            
            # Check if delta is in target range
            if min_delta <= delta <= max_delta:
                contract_type = (contract.get('type') or contract.get('option_type', '')).lower()
                if contract_type == option_type:
                    candidates.append((contract, delta))
        
        if not candidates:
            logger.debug(f"No options found with delta in range {min_delta:.2f}-{max_delta:.2f}")
            return None
        
        # Select option closest to middle of range
        target_delta = (min_delta + max_delta) / 2
        best_contract = min(candidates, key=lambda x: abs(x[1] - target_delta))
        
        logger.info(f"Selected strike with delta {best_contract[1]:.2f} "
                   f"(target range: {min_delta:.2f}-{max_delta:.2f})")
        return best_contract[0]
    
    # ========== PHASE E: EXECUTION OPTIMIZATION ==========
    
    def is_optimal_trading_time(self) -> Tuple[bool, str]:
        """
        Phase E: Check if current time is optimal for trading
        
        Returns:
            (is_optimal, reason)
        """
        now_et = datetime.now(ET)
        current_time = now_et.time()
        
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        # Check if market is open
        if current_time < market_open or current_time > market_close:
            return False, "Market is closed"
        
        # Check first N minutes
        avoid_until = time(
            market_open.hour, 
            market_open.minute + Config.AVOID_FIRST_MINUTES
        )
        if current_time < avoid_until:
            return False, f"Avoid first {Config.AVOID_FIRST_MINUTES} minutes (high volatility)"
        
        # Check last N minutes
        avoid_after = time(
            market_close.hour - 1 if Config.AVOID_LAST_MINUTES > 15 else market_close.hour,
            60 - Config.AVOID_LAST_MINUTES if Config.AVOID_LAST_MINUTES <= 15 else 
            market_close.minute - Config.AVOID_LAST_MINUTES + 60
        )
        # Simplified: avoid after 3:45 PM
        if current_time > time(15, 45):
            return False, f"Avoid last {Config.AVOID_LAST_MINUTES} minutes (low liquidity)"
        
        return True, "Optimal trading window"
    
    def calculate_limit_price(
        self, 
        bid: float, 
        ask: float, 
        side: str
    ) -> float:
        """
        Phase E: Calculate optimal limit price
        
        Args:
            bid: Current bid price
            ask: Current ask price
            side: 'buy' or 'sell'
            
        Returns:
            Suggested limit price
        """
        mid = (bid + ask) / 2
        spread = ask - bid
        offset = mid * Config.LIMIT_ORDER_OFFSET_PCT
        
        if side == 'buy':
            # Buy slightly below mid
            limit_price = mid - min(offset, spread * 0.25)
        else:
            # Sell slightly above mid
            limit_price = mid + min(offset, spread * 0.25)
        
        # Round to nearest cent
        limit_price = round(limit_price, 2)
        
        logger.debug(f"Limit price calculation: bid={bid:.2f}, ask={ask:.2f}, "
                    f"mid={mid:.2f}, limit={limit_price:.2f} ({side})")
        
        return limit_price
    
    def should_use_market_order(self, spread_pct: float) -> Tuple[bool, str]:
        """
        Phase E: Determine if market order should be used
        
        Args:
            spread_pct: Bid-ask spread as percentage of mid price
            
        Returns:
            (use_market, reason)
        """
        if not Config.USE_LIMIT_ORDERS:
            return True, "Limit orders disabled in config"
        
        # Use market order if spread is very tight
        if spread_pct < 0.01:  # < 1% spread
            return True, "Spread < 1% - market order efficient"
        
        # Use limit order for wider spreads
        return False, f"Spread {spread_pct:.1%} - use limit order"
    
    # ========== COMPREHENSIVE CHECK ==========
    
    def pre_trade_check(
        self,
        symbol: str,
        option_type: str,
        dte: int,
        iv_rank: Optional[float],
        confidence: float,
        greeks: Optional[Dict],
        qty: int
    ) -> Tuple[bool, List[str]]:
        """
        Run all pre-trade checks
        
        Args:
            symbol: Underlying symbol
            option_type: 'call' or 'put'
            dte: Days to expiration
            iv_rank: IV Rank percentage (0-100)
            confidence: Signal confidence (0.0 - 1.0)
            greeks: Option Greeks dict (delta, gamma, theta, vega)
            qty: Number of contracts
            
        Returns:
            (allowed, list_of_reasons)
        """
        reasons = []
        
        # Phase B: DTE position sizing (informational)
        size_multiplier = self.get_dte_position_size_multiplier(dte)
        if size_multiplier < 1.0:
            reasons.append(f"⚠️ DTE {dte}: Position size reduced to {size_multiplier:.0%}")
        
        # Phase C: Theta budget
        if greeks:
            theta = greeks.get('theta', 0)
            allowed, reason = self.check_theta_budget(theta * qty * 100)
            if not allowed:
                reasons.append(f"❌ {reason}")
                return False, reasons
            
            # Gamma check
            gamma = greeks.get('gamma', 0)
            allowed, reason = self.check_position_gamma(gamma, qty)
            if not allowed:
                reasons.append(f"❌ {reason}")
                return False, reasons
            
            # Portfolio Greeks
            temp_position = PositionGreeks(
                symbol=symbol,
                delta=greeks.get('delta', 0),
                gamma=greeks.get('gamma', 0),
                theta=greeks.get('theta', 0),
                vega=greeks.get('vega', 0),
                qty=qty,
                dte=dte,
                iv=greeks.get('iv', 0),
                underlying_price=greeks.get('underlying_price', 0)
            )
            allowed, violations = self.check_greeks_limits(temp_position)
            if not allowed:
                for v in violations:
                    reasons.append(f"❌ {v}")
                return False, reasons
        
        # Phase D: IV Rank gate
        if iv_rank is not None:
            allowed, reason = self.check_iv_rank_entry(symbol, iv_rank)
            if not allowed:
                reasons.append(f"❌ {reason}")
                return False, reasons
        
        # Phase E: Time of day
        allowed, reason = self.is_optimal_trading_time()
        if not allowed:
            reasons.append(f"⚠️ TIME: {reason}")
            # Don't block, just warn
        
        if not reasons:
            reasons.append("✅ All pre-trade checks passed")
        
        return True, reasons
    
    def get_portfolio_summary(self) -> Dict:
        """Get summary of portfolio Greeks and risk metrics"""
        return {
            'total_delta': self.portfolio_greeks.total_delta,
            'total_gamma': self.portfolio_greeks.total_gamma,
            'total_theta': self.portfolio_greeks.total_theta,
            'total_vega': self.portfolio_greeks.total_vega,
            'position_count': self.portfolio_greeks.position_count,
            'delta_limit': Config.MAX_PORTFOLIO_DELTA,
            'gamma_limit': Config.MAX_PORTFOLIO_GAMMA,
            'theta_limit': Config.MAX_PORTFOLIO_THETA,
            'vega_limit': Config.MAX_PORTFOLIO_VEGA,
            'delta_pct_used': abs(self.portfolio_greeks.total_delta / Config.MAX_PORTFOLIO_DELTA * 100),
            'gamma_pct_used': abs(self.portfolio_greeks.total_gamma / Config.MAX_PORTFOLIO_GAMMA * 100),
            'theta_pct_used': abs(self.portfolio_greeks.total_theta / Config.MAX_PORTFOLIO_THETA * 100),
            'vega_pct_used': abs(self.portfolio_greeks.total_vega / Config.MAX_PORTFOLIO_VEGA * 100),
        }

