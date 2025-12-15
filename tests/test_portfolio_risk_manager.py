"""
Test Portfolio Risk Manager
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.risk.portfolio_risk_manager import (
    PortfolioRiskManager,
    RiskDecision,
    RiskStatus,
    RiskLevel,
    check_trade_risk
)


def test_trade_blocked_when_delta_exceeded():
    """Test that trade is blocked when delta limit is exceeded"""
    print("="*60)
    print("Test 1: Trade Blocked When Delta Exceeded")
    print("="*60)
    
    # Current positions with high delta
    current_positions = [
        {
            'symbol': 'AAPL',
            'qty': 400,  # 400 shares = 400 delta
            'side': 'long',
            'entry_price': 150.0
        }
    ]
    
    # Proposed trade that would exceed limit
    proposed_trade = {
        'symbol': 'TSLA',
        'qty': 200,  # Would add 200 delta, total = 600 (exceeds 500)
        'side': 'long',
        'entry_price': 200.0
    }
    
    limits = {'max_abs_delta': 500}
    manager = PortfolioRiskManager(limits=limits)
    
    decision = manager.check_trade_allowed(current_positions, proposed_trade)
    
    print(f"Decision: {decision.allowed}")
    print(f"Reason: {decision.reason}")
    print(f"Risk Level: {decision.risk_level.value}")
    print(f"Current Delta: {decision.current_greeks.get('delta')}")
    print(f"Projected Delta: {decision.projected_greeks.get('delta')}")
    
    assert not decision.allowed, "Trade should be blocked"
    assert 'Delta' in decision.reason, "Reason should mention Delta"
    assert decision.risk_level in [RiskLevel.WARNING, RiskLevel.DANGER], "Should be warning or danger"
    assert decision.projected_greeks['delta'] > 500, "Projected delta should exceed limit"
    
    print("✅ Test 1 PASSED\n")


def test_trade_blocked_when_theta_exceeded():
    """Test that trade is blocked when theta limit is exceeded"""
    print("="*60)
    print("Test 2: Trade Blocked When Theta Exceeded")
    print("="*60)
    
    # Current positions with high theta (negative)
    current_positions = [
        {
            'symbol': 'AAPL',
            'qty': 20,  # 20 contracts
            'side': 'long',
            'entry_price': 5.0,
            'option_type': 'call',
            'strike': 150.0,
            'expiration_date': '2025-12-20',
            'delta': 0.5,
            'gamma': 0.02,
            'theta': -0.15,  # -0.15 per contract
            'vega': 0.15
        }
    ]
    
    # Calculate current theta: 20 contracts * -0.15 * 100 = -300
    # Limit is -300, so we're at the limit
    
    # Proposed trade that would exceed limit
    proposed_trade = {
        'symbol': 'TSLA',
        'qty': 5,  # 5 more contracts
        'side': 'long',
        'entry_price': 3.0,
        'option_type': 'call',
        'strike': 200.0,
        'expiration_date': '2025-12-20',
        'delta': 0.5,
        'gamma': 0.02,
        'theta': -0.15,  # Would add -75 theta, total = -375 (exceeds -300)
        'vega': 0.15
    }
    
    limits = {'max_theta_per_day': -300}
    manager = PortfolioRiskManager(limits=limits)
    
    decision = manager.check_trade_allowed(current_positions, proposed_trade)
    
    print(f"Decision: {decision.allowed}")
    print(f"Reason: {decision.reason}")
    print(f"Current Theta: {decision.current_greeks.get('theta')}")
    print(f"Projected Theta: {decision.projected_greeks.get('theta')}")
    
    assert not decision.allowed, "Trade should be blocked"
    assert 'Theta' in decision.reason, "Reason should mention Theta"
    assert decision.projected_greeks['theta'] < -300, "Projected theta should exceed limit"
    
    print("✅ Test 2 PASSED\n")


def test_trade_allowed_when_within_limits():
    """Test that trade is allowed when within limits"""
    print("="*60)
    print("Test 3: Trade Allowed When Within Limits")
    print("="*60)
    
    # Current positions
    current_positions = [
        {
            'symbol': 'AAPL',
            'qty': 100,  # 100 shares = 100 delta
            'side': 'long',
            'entry_price': 150.0
        }
    ]
    
    # Proposed trade that stays within limits
    proposed_trade = {
        'symbol': 'TSLA',
        'qty': 200,  # Would add 200 delta, total = 300 (within 500 limit)
        'side': 'long',
        'entry_price': 200.0
    }
    
    limits = {'max_abs_delta': 500}
    manager = PortfolioRiskManager(limits=limits)
    
    decision = manager.check_trade_allowed(current_positions, proposed_trade)
    
    print(f"Decision: {decision.allowed}")
    print(f"Reason: {decision.reason}")
    print(f"Current Delta: {decision.current_greeks.get('delta')}")
    print(f"Projected Delta: {decision.projected_greeks.get('delta')}")
    
    assert decision.allowed, "Trade should be allowed"
    assert decision.risk_level == RiskLevel.SAFE, "Should be safe"
    assert decision.projected_greeks['delta'] <= 500, "Projected delta should be within limit"
    
    print("✅ Test 3 PASSED\n")


def test_hard_violation_triggers_forced_reduction():
    """Test that hard violation triggers forced reduction"""
    print("="*60)
    print("Test 4: Hard Violation Triggers Forced Reduction")
    print("="*60)
    
    # Current positions with extreme delta (hard violation = 1.5x limit = 750)
    current_positions = [
        {
            'symbol': 'AAPL',
            'qty': 800,  # 800 shares = 800 delta (exceeds 1.5 * 500 = 750)
            'side': 'long',
            'entry_price': 150.0
        },
        {
            'symbol': 'TSLA',
            'qty': 100,  # 100 shares = 100 delta
            'side': 'long',
            'entry_price': 200.0
        }
    ]
    
    limits = {'max_abs_delta': 500}
    manager = PortfolioRiskManager(limits=limits, violation_threshold=1.5)
    
    # Check portfolio health
    status = manager.check_portfolio_health(current_positions)
    
    print(f"Risk Level: {status.risk_level.value}")
    print(f"Violations: {status.violations}")
    print(f"Delta: {status.greeks.delta}")
    
    assert status.risk_level == RiskLevel.DANGER, "Should be danger level"
    assert len(status.violations) > 0, "Should have violations"
    
    # Force reduction
    actions = manager.force_reduce_if_needed(current_positions)
    
    print(f"Reduction Actions: {len(actions)}")
    for action in actions:
        print(f"  - {action.action_type}: {action.symbol} qty={action.qty}")
    
    assert len(actions) > 0, "Should generate reduction actions"
    assert any(a.action_type == 'close_position' for a in actions), "Should close positions"
    
    print("✅ Test 4 PASSED\n")


def test_convenience_function():
    """Test convenience function"""
    print("="*60)
    print("Test 5: Convenience Function")
    print("="*60)
    
    current_positions = [
        {
            'symbol': 'AAPL',
            'qty': 100,
            'side': 'long',
            'entry_price': 150.0
        }
    ]
    
    proposed_trade = {
        'symbol': 'TSLA',
        'qty': 200,
        'side': 'long',
        'entry_price': 200.0
    }
    
    limits = {'max_abs_delta': 500}
    decision = check_trade_risk(current_positions, proposed_trade, limits=limits)
    
    print(f"Decision: {decision.allowed}")
    print(f"Risk Level: {decision.risk_level.value}")
    
    assert decision.allowed, "Trade should be allowed"
    print("✅ Test 5 PASSED\n")


def test_mixed_stock_and_options():
    """Test with mixed stock and options positions"""
    print("="*60)
    print("Test 6: Mixed Stock and Options")
    print("="*60)
    
    current_positions = [
        {
            'symbol': 'AAPL',
            'qty': 200,  # 200 shares = 200 delta
            'side': 'long',
            'entry_price': 150.0
        },
        {
            'symbol': 'TSLA',
            'qty': 10,  # 10 contracts
            'side': 'long',
            'entry_price': 5.0,
            'option_type': 'call',
            'strike': 200.0,
            'expiration_date': '2025-12-20',
            'delta': 0.5,  # 10 * 0.5 * 100 = 500 delta
            'gamma': 0.02,
            'theta': -0.1,
            'vega': 0.15
        }
    ]
    
    # Total delta = 200 + 500 = 700 (exceeds 500)
    
    limits = {'max_abs_delta': 500}
    manager = PortfolioRiskManager(limits=limits)
    
    status = manager.check_portfolio_health(current_positions)
    
    print(f"Risk Level: {status.risk_level.value}")
    print(f"Delta: {status.greeks.delta}")
    print(f"Within Limits: {status.within_limits}")
    
    assert not status.within_limits, "Should be outside limits"
    assert abs(status.greeks.delta) > 500, "Delta should exceed limit"
    
    print("✅ Test 6 PASSED\n")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Portfolio Risk Manager - Test Suite")
    print("="*60 + "\n")
    
    try:
        test_trade_blocked_when_delta_exceeded()
        test_trade_blocked_when_theta_exceeded()
        test_trade_allowed_when_within_limits()
        test_hard_violation_triggers_forced_reduction()
        test_convenience_function()
        test_mixed_stock_and_options()
        
        print("="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

