"""
Test UVaR Calculator
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from core.risk.uvar import UVaRCalculator, UVaRResult, calculate_uvar
from datetime import datetime, timedelta


def test_uvar_within_limits():
    """Test UVaR calculation when within limits"""
    print("="*60)
    print("Test 1: UVaR Within Limits")
    print("="*60)
    
    calculator = UVaRCalculator(
        confidence=0.99,
        max_uvar_1d=-1500.0,
        max_uvar_3d=-3000.0
    )
    
    # Generate P&L history (mostly positive, some losses)
    np.random.seed(42)
    pnl_history = np.random.normal(50, 200, 90)  # Mean $50, std $200
    
    # Add some tail losses
    pnl_history[0:5] = [-500, -600, -700, -800, -900]
    
    for pnl in pnl_history:
        calculator.add_daily_pnl(float(pnl))
    
    result = calculator.calculate_uvar(horizon_days=1, current_portfolio_value=10000.0)
    
    print(f"UVaR 1-day: ${result.uvar_1d:.2f}")
    print(f"UVaR 3-day: ${result.uvar_3d:.2f}")
    print(f"Status: {result.status}")
    print(f"Sample size: {result.sample_size}")
    
    # Check if within limits
    within_limits, reason, _ = calculator.check_uvar_limit(
        current_portfolio_value=10000.0,
        horizon_days=1
    )
    
    print(f"Within limits: {within_limits}")
    print(f"Reason: {reason}")
    
    # Should be within limits (UVaR should be around -800 to -900, which is > -1500)
    assert result.sample_size >= 30, "Should have enough data"
    assert result.uvar_1d < 0, "UVaR should be negative"
    print("✅ Test 1 PASSED\n")


def test_uvar_breach():
    """Test UVaR calculation when limit is breached"""
    print("="*60)
    print("Test 2: UVaR Breach")
    print("="*60)
    
    calculator = UVaRCalculator(
        confidence=0.99,
        max_uvar_1d=-1500.0,
        max_uvar_3d=-3000.0
    )
    
    # Generate P&L history with extreme losses
    np.random.seed(42)
    pnl_history = np.random.normal(-100, 300, 90)  # Mean -$100, std $300
    
    # Add extreme tail losses
    pnl_history[0:10] = [-2000, -2500, -3000, -3500, -4000, -1500, -1800, -2200, -2800, -3200]
    
    for pnl in pnl_history:
        calculator.add_daily_pnl(float(pnl))
    
    result = calculator.calculate_uvar(horizon_days=1, current_portfolio_value=10000.0)
    
    print(f"UVaR 1-day: ${result.uvar_1d:.2f}")
    print(f"Limit: ${calculator.max_uvar_1d:.2f}")
    print(f"Status: {result.status}")
    
    # Check if within limits
    within_limits, reason, _ = calculator.check_uvar_limit(
        current_portfolio_value=10000.0,
        horizon_days=1
    )
    
    print(f"Within limits: {within_limits}")
    print(f"Reason: {reason}")
    
    # Should breach limit (UVaR should be around -2000 to -3000, which is < -1500)
    assert not within_limits, "Should breach limit"
    assert 'exceeds limit' in reason, "Reason should mention limit"
    assert result.status in ['warning', 'danger'], "Should be warning or danger"
    
    print("✅ Test 2 PASSED\n")


def test_extreme_uvar_triggers_danger():
    """Test that extreme UVaR triggers danger status"""
    print("="*60)
    print("Test 3: Extreme UVaR Triggers Danger")
    print("="*60)
    
    calculator = UVaRCalculator(
        confidence=0.99,
        max_uvar_1d=-1500.0,
        max_uvar_3d=-3000.0
    )
    
    # Generate P&L history with very extreme losses (2x limit)
    np.random.seed(42)
    pnl_history = np.random.normal(-200, 500, 90)
    
    # Add extreme tail losses (2x limit = -3000)
    pnl_history[0:15] = [-3000, -3500, -4000, -4500, -5000, -3200, -3800, -4200, -4800, -5200,
                          -3100, -3600, -4100, -4600, -5100]
    
    for pnl in pnl_history:
        calculator.add_daily_pnl(float(pnl))
    
    result = calculator.calculate_uvar(horizon_days=1, current_portfolio_value=10000.0)
    
    print(f"UVaR 1-day: ${result.uvar_1d:.2f}")
    print(f"Limit: ${calculator.max_uvar_1d:.2f}")
    print(f"2x Limit: ${calculator.max_uvar_1d * 2:.2f}")
    print(f"Status: {result.status}")
    
    # Should be danger status (UVaR < 2x limit)
    assert result.status == 'danger', f"Should be danger, got {result.status}"
    assert result.uvar_1d < calculator.max_uvar_1d * 2, "UVaR should exceed 2x limit"
    
    print("✅ Test 3 PASSED\n")


def test_insufficient_data():
    """Test behavior with insufficient data"""
    print("="*60)
    print("Test 4: Insufficient Data")
    print("="*60)
    
    calculator = UVaRCalculator(
        confidence=0.99,
        max_uvar_1d=-1500.0
    )
    
    # Add only 10 days of data (need 30+)
    for i in range(10):
        calculator.add_daily_pnl(-100.0)
    
    result = calculator.calculate_uvar(horizon_days=1)
    
    print(f"UVaR 1-day: ${result.uvar_1d:.2f}")
    print(f"Status: {result.status}")
    print(f"Sample size: {result.sample_size}")
    
    # Should return conservative default
    assert result.sample_size < 30, "Should have insufficient data"
    assert result.status == 'warning', "Should be warning with insufficient data"
    assert result.uvar_1d == -2000.0, "Should return conservative default"
    
    print("✅ Test 4 PASSED\n")


def test_convenience_function():
    """Test convenience function"""
    print("="*60)
    print("Test 5: Convenience Function")
    print("="*60)
    
    # Generate P&L history
    np.random.seed(42)
    pnl_history = np.random.normal(50, 200, 90).tolist()
    pnl_history[0:5] = [-500, -600, -700, -800, -900]
    
    uvar = calculate_uvar(pnl_history, confidence=0.99, horizon_days=1)
    
    print(f"UVaR: ${uvar:.2f}")
    
    assert uvar < 0, "UVaR should be negative"
    assert abs(uvar) < 2000, "UVaR should be reasonable"
    
    print("✅ Test 5 PASSED\n")


def test_pnl_statistics():
    """Test P&L statistics"""
    print("="*60)
    print("Test 6: P&L Statistics")
    print("="*60)
    
    calculator = UVaRCalculator()
    
    # Generate P&L history
    np.random.seed(42)
    pnl_history = np.random.normal(50, 200, 90)
    
    for pnl in pnl_history:
        calculator.add_daily_pnl(float(pnl))
    
    stats = calculator.get_pnl_statistics()
    
    print(f"Count: {stats['count']}")
    print(f"Mean: ${stats['mean']:.2f}")
    print(f"Std: ${stats['std']:.2f}")
    print(f"Min: ${stats['min']:.2f}")
    print(f"Max: ${stats['max']:.2f}")
    print(f"1st percentile: ${stats['percentile_1']:.2f}")
    print(f"99th percentile: ${stats['percentile_99']:.2f}")
    
    assert stats['count'] == 90, "Should have 90 observations"
    assert 'mean' in stats, "Should have mean"
    assert 'std' in stats, "Should have std"
    
    print("✅ Test 6 PASSED\n")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("UVaR Calculator - Test Suite")
    print("="*60 + "\n")
    
    try:
        test_uvar_within_limits()
        test_uvar_breach()
        test_extreme_uvar_triggers_danger()
        test_insufficient_data()
        test_convenience_function()
        test_pnl_statistics()
        
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

