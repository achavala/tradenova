"""
Portfolio Risk Manager - Step 2
Enforces portfolio-level risk limits and circuit breakers.

This sits ABOVE all trading decisions (RL, signals, execution).
No trade may be placed if it increases portfolio risk beyond defined limits.

Architecture:
    Portfolio Risk Manager (authoritative gatekeeper)
      ↓
    RL Agent / Signal Agents
      ↓
    Execution Engine
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from core.risk.portfolio_greeks import PortfolioGreeksAggregator, PortfolioGreeks
from core.risk.uvar import UVaRCalculator

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk violation levels"""
    SAFE = "safe"
    WARNING = "warning"  # Soft violation - block new trades
    DANGER = "danger"  # Hard violation - force reduction
    BLOCKED = "blocked"  # Extreme violation - freeze trading


@dataclass
class RiskDecision:
    """Decision from risk manager"""
    allowed: bool
    reason: str
    risk_level: RiskLevel
    projected_greeks: Optional[Dict] = None
    current_greeks: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'allowed': self.allowed,
            'reason': self.reason,
            'risk_level': self.risk_level.value,
            'projected_greeks': self.projected_greeks,
            'current_greeks': self.current_greeks
        }


@dataclass
class RiskStatus:
    """Current portfolio risk status"""
    risk_level: RiskLevel
    violations: List[str]
    greeks: PortfolioGreeks
    within_limits: bool
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'risk_level': self.risk_level.value,
            'violations': self.violations,
            'greeks': self.greeks.to_dict(),
            'within_limits': self.within_limits,
            'recommendations': self.recommendations
        }


@dataclass
class Action:
    """Action to reduce risk"""
    action_type: str  # 'close_position', 'reduce_position', 'freeze_trading'
    symbol: str
    qty: float
    reason: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'action_type': self.action_type,
            'symbol': self.symbol,
            'qty': self.qty,
            'reason': self.reason
        }


class PortfolioRiskManager:
    """
    Portfolio Risk Manager
    
    Enforces hard limits on portfolio Greeks.
    Sits above all trading decisions.
    """
    
    def __init__(
        self,
        limits: Optional[Dict] = None,
        greeks_aggregator: Optional[PortfolioGreeksAggregator] = None,
        uvar_calculator: Optional[UVaRCalculator] = None,
        violation_threshold: float = 1.5,  # Hard violation = 1.5x limit
        enable_uvar: bool = True  # Enable UVaR checks
    ):
        """
        Initialize risk manager
        
        Args:
            limits: Risk limits dictionary. Default:
                {
                    "max_abs_delta": 500,
                    "max_theta_per_day": -300,  # Negative (theta is usually negative)
                    "max_gamma": 25,
                    "max_vega": 300,
                    "max_uvar_1d": -1500.0,
                    "max_uvar_3d": -3000.0
                }
            greeks_aggregator: Optional PortfolioGreeksAggregator instance
            uvar_calculator: Optional UVaRCalculator instance
            violation_threshold: Multiplier for hard violations (default 1.5x)
            enable_uvar: Enable UVaR checks (default True)
        """
        # Default limits (conservative)
        self.limits = limits or {
            "max_abs_delta": 500,
            "max_theta_per_day": -300,  # Negative (theta is usually negative for long options)
            "max_gamma": 25,
            "max_vega": 300,
            "max_uvar_1d": -1500.0,
            "max_uvar_3d": -3000.0
        }
        
        self.violation_threshold = violation_threshold
        self.greeks_aggregator = greeks_aggregator or PortfolioGreeksAggregator()
        self.uvar_calculator = uvar_calculator or UVaRCalculator(
            max_uvar_1d=self.limits.get("max_uvar_1d", -1500.0),
            max_uvar_3d=self.limits.get("max_uvar_3d", -3000.0)
        )
        self.enable_uvar = enable_uvar
        
        logger.info(f"Portfolio Risk Manager initialized with limits: {self.limits}")
        logger.info(f"UVaR checks: {'enabled' if self.enable_uvar else 'disabled'}")
    
    def check_trade_allowed(
        self,
        current_positions: List[Dict],
        proposed_trade: Dict,
        current_prices: Optional[Dict[str, float]] = None
    ) -> RiskDecision:
        """
        Check if a proposed trade is allowed given current portfolio
        
        Args:
            current_positions: List of current position dictionaries
            proposed_trade: Proposed trade dictionary with:
                - symbol: str
                - qty: float (positive for buy, negative for sell)
                - side: 'long' or 'short'
                - option_type: Optional[str] - 'call' or 'put'
                - strike: Optional[float]
                - expiration_date: Optional[str]
                - delta, gamma, theta, vega: Optional[float] (if known)
            current_prices: Optional dict of current prices by symbol
        
        Returns:
            RiskDecision object
        """
        # Get current portfolio Greeks
        current_greeks = self.greeks_aggregator.aggregate_greeks(
            positions=current_positions,
            current_prices=current_prices
        )
        
        # Clone positions and apply proposed trade
        projected_positions = self._apply_trade_to_positions(
            current_positions=current_positions,
            proposed_trade=proposed_trade
        )
        
        # Get projected portfolio Greeks
        projected_greeks = self.greeks_aggregator.aggregate_greeks(
            positions=projected_positions,
            current_prices=current_prices
        )
        
        # Check limits (Greeks first, then UVaR)
        violations = self._check_limits(projected_greeks)
        
        # Check UVaR if enabled
        uvar_violation = None
        if self.enable_uvar:
            uvar_within_limits, uvar_reason, uvar_result = self.uvar_calculator.check_uvar_limit(
                current_portfolio_value=None,  # Could pass portfolio value if available
                horizon_days=1
            )
            if not uvar_within_limits:
                uvar_violation = uvar_reason
                violations.append(f"UVaR: {uvar_reason}")
        
        if not violations:
            # All limits satisfied
            return RiskDecision(
                allowed=True,
                reason="All limits satisfied",
                risk_level=RiskLevel.SAFE,
                projected_greeks=projected_greeks.to_dict(),
                current_greeks=current_greeks.to_dict()
            )
        
        # Check if hard violation
        risk_level = self._determine_risk_level(projected_greeks, violations)
        
        # Block trade if any violation
        return RiskDecision(
            allowed=False,
            reason=f"Risk limit violated: {', '.join(violations)}",
            risk_level=risk_level,
            projected_greeks=projected_greeks.to_dict(),
            current_greeks=current_greeks.to_dict()
        )
    
    def check_portfolio_health(
        self,
        positions: List[Dict],
        current_prices: Optional[Dict[str, float]] = None,
        current_portfolio_value: Optional[float] = None
    ) -> RiskStatus:
        """
        Check current portfolio health
        
        Args:
            positions: List of current position dictionaries
            current_prices: Optional dict of current prices by symbol
            current_portfolio_value: Optional current portfolio value for UVaR
        
        Returns:
            RiskStatus object
        """
        greeks = self.greeks_aggregator.aggregate_greeks(
            positions=positions,
            current_prices=current_prices
        )
        
        violations = self._check_limits(greeks)
        
        # Check UVaR if enabled
        if self.enable_uvar:
            uvar_within_limits, uvar_reason, uvar_result = self.uvar_calculator.check_uvar_limit(
                current_portfolio_value=current_portfolio_value,
                horizon_days=1
            )
            if not uvar_within_limits:
                violations.append(f"UVaR: {uvar_reason}")
        
        risk_level = self._determine_risk_level(greeks, violations)
        
        recommendations = []
        if violations:
            recommendations = self._generate_recommendations(greeks, violations)
        
        return RiskStatus(
            risk_level=risk_level,
            violations=violations,
            greeks=greeks,
            within_limits=len(violations) == 0,
            recommendations=recommendations
        )
    
    def force_reduce_if_needed(
        self,
        positions: List[Dict],
        current_prices: Optional[Dict[str, float]] = None
    ) -> List[Action]:
        """
        Force position reductions if hard violations exist
        
        Args:
            positions: List of current position dictionaries
            current_prices: Optional dict of current prices by symbol
        
        Returns:
            List of Action objects to reduce risk
        """
        status = self.check_portfolio_health(positions, current_prices)
        
        if status.risk_level != RiskLevel.DANGER:
            # No hard violation, no action needed
            return []
        
        # Generate reduction actions
        actions = []
        
        # Strategy: Close highest-risk positions first
        # Sort positions by absolute delta (highest first)
        positions_with_delta = []
        for pos in positions:
            # Estimate delta contribution
            if pos.get('option_type'):
                # Options position
                delta = pos.get('delta', 0.5)  # Default delta if not known
                qty = abs(pos.get('qty', 0))
                contract_multiplier = 100.0
                delta_contribution = abs(delta * qty * contract_multiplier)
            else:
                # Stock position
                qty = abs(pos.get('qty', 0))
                delta_contribution = qty
            
            positions_with_delta.append((delta_contribution, pos))
        
        # Sort by delta contribution (highest first)
        positions_with_delta.sort(key=lambda x: x[0], reverse=True)
        
        # Close positions until within limits
        remaining_positions = positions.copy()
        target_greeks = status.greeks
        
        for delta_contribution, pos in positions_with_delta:
            # Check if we're still in violation
            temp_status = self.check_portfolio_health(remaining_positions, current_prices)
            if temp_status.risk_level != RiskLevel.DANGER:
                break
            
            # Close this position
            symbol = pos.get('symbol')
            qty = pos.get('qty', 0)
            
            actions.append(Action(
                action_type='close_position',
                symbol=symbol,
                qty=qty,
                reason=f"Hard violation reduction: {', '.join(temp_status.violations)}"
            ))
            
            # Remove from remaining positions
            remaining_positions = [p for p in remaining_positions if p.get('symbol') != symbol]
        
        if actions:
            logger.warning(f"Force reduction: {len(actions)} positions to close due to hard violations")
        
        return actions
    
    def _apply_trade_to_positions(
        self,
        current_positions: List[Dict],
        proposed_trade: Dict
    ) -> List[Dict]:
        """Apply proposed trade to current positions (clone)"""
        # Deep copy positions
        projected = [pos.copy() for pos in current_positions]
        
        symbol = proposed_trade.get('symbol')
        trade_qty = proposed_trade.get('qty', 0)
        trade_side = proposed_trade.get('side', 'long')
        
        # Check if position already exists
        existing_idx = None
        for i, pos in enumerate(projected):
            if pos.get('symbol') == symbol:
                existing_idx = i
                break
        
        if existing_idx is not None:
            # Update existing position
            existing = projected[existing_idx]
            current_qty = existing.get('qty', 0)
            
            # Adjust quantity
            if trade_side == 'long':
                new_qty = current_qty + trade_qty
            else:
                new_qty = current_qty - trade_qty
            
            existing['qty'] = new_qty
            
            # Update Greeks if provided
            if 'delta' in proposed_trade:
                existing['delta'] = proposed_trade.get('delta')
            if 'gamma' in proposed_trade:
                existing['gamma'] = proposed_trade.get('gamma')
            if 'theta' in proposed_trade:
                existing['theta'] = proposed_trade.get('theta')
            if 'vega' in proposed_trade:
                existing['vega'] = proposed_trade.get('vega')
        else:
            # New position
            new_pos = proposed_trade.copy()
            projected.append(new_pos)
        
        return projected
    
    def _check_limits(self, greeks: PortfolioGreeks) -> List[str]:
        """Check if Greeks violate limits"""
        violations = []
        
        # Check Delta
        max_delta = self.limits.get('max_abs_delta', float('inf'))
        if abs(greeks.delta) > max_delta:
            violations.append(f"Delta: {greeks.delta:.2f} exceeds limit ±{max_delta}")
        
        # Check Theta (theta is usually negative, so check if more negative than limit)
        max_theta = self.limits.get('max_theta_per_day', float('-inf'))
        if greeks.theta < max_theta:  # max_theta is negative, so < means more negative
            violations.append(f"Theta: {greeks.theta:.2f} exceeds limit {max_theta}")
        
        # Check Gamma
        max_gamma = self.limits.get('max_gamma', float('inf'))
        if abs(greeks.gamma) > max_gamma:
            violations.append(f"Gamma: {abs(greeks.gamma):.4f} exceeds limit {max_gamma}")
        
        # Check Vega
        max_vega = self.limits.get('max_vega', float('inf'))
        if abs(greeks.vega) > max_vega:
            violations.append(f"Vega: {abs(greeks.vega):.2f} exceeds limit {max_vega}")
        
        return violations
    
    def _determine_risk_level(
        self,
        greeks: PortfolioGreeks,
        violations: List[str]
    ) -> RiskLevel:
        """Determine risk level based on violations"""
        if not violations:
            return RiskLevel.SAFE
        
        # Check if hard violation (exceeds threshold)
        max_delta = self.limits.get('max_abs_delta', float('inf'))
        max_theta = self.limits.get('max_theta_per_day', float('-inf'))
        max_gamma = self.limits.get('max_gamma', float('inf'))
        max_vega = self.limits.get('max_vega', float('inf'))
        
        # Hard violation if exceeds threshold
        hard_violation = False
        
        if abs(greeks.delta) > max_delta * self.violation_threshold:
            hard_violation = True
        if greeks.theta < max_theta * self.violation_threshold:
            hard_violation = True
        if abs(greeks.gamma) > max_gamma * self.violation_threshold:
            hard_violation = True
        if abs(greeks.vega) > max_vega * self.violation_threshold:
            hard_violation = True
        
        if hard_violation:
            return RiskLevel.DANGER
        
        # Soft violation
        return RiskLevel.WARNING
    
    def _generate_recommendations(
        self,
        greeks: PortfolioGreeks,
        violations: List[str]
    ) -> List[str]:
        """Generate recommendations to reduce risk"""
        recommendations = []
        
        max_delta = self.limits.get('max_abs_delta', float('inf'))
        max_theta = self.limits.get('max_theta_per_day', float('-inf'))
        
        if abs(greeks.delta) > max_delta:
            excess = abs(greeks.delta) - max_delta
            recommendations.append(f"Reduce Delta by {excess:.0f} (current: {greeks.delta:.2f}, limit: ±{max_delta})")
        
        if greeks.theta < max_theta:
            excess = abs(greeks.theta - max_theta)
            recommendations.append(f"Reduce Theta by {excess:.0f} (current: {greeks.theta:.2f}, limit: {max_theta})")
        
        if abs(greeks.gamma) > self.limits.get('max_gamma', float('inf')):
            recommendations.append(f"Reduce Gamma (current: {greeks.gamma:.4f})")
        
        if abs(greeks.vega) > self.limits.get('max_vega', float('inf')):
            recommendations.append(f"Reduce Vega (current: {greeks.vega:.2f})")
        
        return recommendations
    
    def update_limits(self, new_limits: Dict):
        """Update risk limits"""
        self.limits.update(new_limits)
        logger.info(f"Risk limits updated: {self.limits}")


# Convenience function
def check_trade_risk(
    current_positions: List[Dict],
    proposed_trade: Dict,
    limits: Optional[Dict] = None,
    current_prices: Optional[Dict[str, float]] = None
) -> RiskDecision:
    """
    Convenience function to check trade risk
    
    Args:
        current_positions: List of current position dictionaries
        proposed_trade: Proposed trade dictionary
        limits: Optional risk limits dictionary
        current_prices: Optional dict of current prices by symbol
    
    Returns:
        RiskDecision object
    """
    manager = PortfolioRiskManager(limits=limits)
    return manager.check_trade_allowed(
        current_positions=current_positions,
        proposed_trade=proposed_trade,
        current_prices=current_prices
    )

