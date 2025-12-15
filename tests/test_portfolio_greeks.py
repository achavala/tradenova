"""
Test Portfolio Greeks Aggregator
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.risk.portfolio_greeks import PortfolioGreeksAggregator, PortfolioGreeks, get_portfolio_greeks
from datetime import datetime


def test_stock_positions():
    """Test aggregation with stock positions (no Greeks)"""
    print("="*60)
    print("Test 1: Stock Positions (No Greeks)")
    print("="*60)
    
    positions = [
        {
            'symbol': 'AAPL',
            'qty': 100,
            'side': 'long',
            'entry_price': 150.0
        },
        {
            'symbol': 'TSLA',
            'qty': 50,
            'side': 'short',
            'entry_price': 200.0
        }
    ]
    
    aggregator = PortfolioGreeksAggregator()
    greeks = aggregator.aggregate_greeks(positions)
    
    print(f"Portfolio Greeks:")
    print(f"  Delta: {greeks.delta:.2f} (Expected: 100 - 50 = 50)")
    print(f"  Gamma: {greeks.gamma:.4f} (Expected: 0.0)")
    print(f"  Theta: {greeks.theta:.2f} (Expected: 0.0)")
    print(f"  Vega: {greeks.vega:.2f} (Expected: 0.0)")
    print(f"  Positions: {greeks.positions_count}")
    
    assert abs(greeks.delta - 50.0) < 0.01, f"Expected delta ~50, got {greeks.delta}"
    assert abs(greeks.gamma) < 0.0001, f"Expected gamma ~0, got {greeks.gamma}"
    print("✅ Test 1 PASSED\n")


def test_options_positions():
    """Test aggregation with options positions (with Greeks)"""
    print("="*60)
    print("Test 2: Options Positions (With Greeks)")
    print("="*60)
    
    positions = [
        {
            'symbol': 'AAPL',
            'qty': 10,  # 10 contracts
            'side': 'long',
            'entry_price': 5.0,
            'option_type': 'call',
            'strike': 150.0,
            'expiration_date': '2025-12-20',
            'delta': 0.5,
            'gamma': 0.02,
            'theta': -0.1,
            'vega': 0.15
        },
        {
            'symbol': 'TSLA',
            'qty': 5,  # 5 contracts
            'side': 'short',
            'entry_price': 3.0,
            'option_type': 'put',
            'strike': 200.0,
            'expiration_date': '2025-12-20',
            'delta': -0.3,
            'gamma': 0.01,
            'theta': 0.05,
            'vega': 0.10
        }
    ]
    
    aggregator = PortfolioGreeksAggregator()
    greeks = aggregator.aggregate_greeks(positions)
    
    print(f"Portfolio Greeks:")
    print(f"  Delta: {greeks.delta:.2f}")
    print(f"    Long call: 10 contracts * 0.5 delta * 100 = 500")
    print(f"    Short put: -5 contracts * -0.3 delta * 100 = 150")
    print(f"    Expected: 500 + 150 = 650")
    print(f"  Gamma: {greeks.gamma:.4f}")
    print(f"    Long call: 10 * 0.02 * 100 = 20")
    print(f"    Short put: -5 * 0.01 * 100 = -5")
    print(f"    Expected: 20 - 5 = 15")
    print(f"  Theta: {greeks.theta:.2f}")
    print(f"    Long call: 10 * -0.1 * 100 = -100")
    print(f"    Short put: -5 * 0.05 * 100 = -25")
    print(f"    Expected: -100 - 25 = -125")
    print(f"  Vega: {greeks.vega:.2f}")
    print(f"    Long call: 10 * 0.15 * 100 = 150")
    print(f"    Short put: -5 * 0.10 * 100 = -50")
    print(f"    Expected: 150 - 50 = 100")
    print(f"  Positions: {greeks.positions_count}")
    
    # Verify calculations
    expected_delta = (10 * 0.5 * 100) + (-5 * -0.3 * 100)  # 500 + 150 = 650
    expected_gamma = (10 * 0.02 * 100) + (-5 * 0.01 * 100)  # 20 - 5 = 15
    expected_theta = (10 * -0.1 * 100) + (-5 * 0.05 * 100)  # -100 - 25 = -125
    expected_vega = (10 * 0.15 * 100) + (-5 * 0.10 * 100)  # 150 - 50 = 100
    
    assert abs(greeks.delta - expected_delta) < 1.0, f"Delta mismatch: {greeks.delta} vs {expected_delta}"
    assert abs(greeks.gamma - expected_gamma) < 0.1, f"Gamma mismatch: {greeks.gamma} vs {expected_gamma}"
    assert abs(greeks.theta - expected_theta) < 1.0, f"Theta mismatch: {greeks.theta} vs {expected_theta}"
    assert abs(greeks.vega - expected_vega) < 1.0, f"Vega mismatch: {greeks.vega} vs {expected_vega}"
    print("✅ Test 2 PASSED\n")


def test_mixed_positions():
    """Test aggregation with mixed stock and options positions"""
    print("="*60)
    print("Test 3: Mixed Stock + Options Positions")
    print("="*60)
    
    positions = [
        {
            'symbol': 'AAPL',
            'qty': 100,
            'side': 'long',
            'entry_price': 150.0
            # Stock position, no Greeks
        },
        {
            'symbol': 'TSLA',
            'qty': 10,  # 10 contracts
            'side': 'long',
            'entry_price': 5.0,
            'option_type': 'call',
            'strike': 200.0,
            'expiration_date': '2025-12-20',
            'delta': 0.5,
            'gamma': 0.02,
            'theta': -0.1,
            'vega': 0.15
        }
    ]
    
    aggregator = PortfolioGreeksAggregator()
    greeks = aggregator.aggregate_greeks(positions)
    
    print(f"Portfolio Greeks:")
    print(f"  Delta: {greeks.delta:.2f}")
    print(f"    Stock: 100 shares * 1.0 delta = 100")
    print(f"    Options: 10 contracts * 0.5 delta * 100 = 500")
    print(f"    Expected: 100 + 500 = 600")
    print(f"  Gamma: {greeks.gamma:.4f} (from options only)")
    print(f"  Theta: {greeks.theta:.2f} (from options only)")
    print(f"  Vega: {greeks.vega:.2f} (from options only)")
    print(f"  Positions: {greeks.positions_count}")
    
    expected_delta = 100 + (10 * 0.5 * 100)  # 100 + 500 = 600
    assert abs(greeks.delta - expected_delta) < 1.0, f"Delta mismatch: {greeks.delta} vs {expected_delta}"
    assert greeks.positions_count == 2, f"Expected 2 positions, got {greeks.positions_count}"
    print("✅ Test 3 PASSED\n")


def test_convenience_function():
    """Test convenience function"""
    print("="*60)
    print("Test 4: Convenience Function")
    print("="*60)
    
    positions = [
        {
            'symbol': 'AAPL',
            'qty': 100,
            'side': 'long',
            'entry_price': 150.0
        }
    ]
    
    greeks = get_portfolio_greeks(positions)
    
    print(f"Portfolio Greeks (via convenience function):")
    print(f"  Delta: {greeks.delta:.2f}")
    print(f"  Positions: {greeks.positions_count}")
    
    assert greeks.delta == 100.0, f"Expected delta 100, got {greeks.delta}"
    print("✅ Test 4 PASSED\n")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Portfolio Greeks Aggregator - Test Suite")
    print("="*60 + "\n")
    
    try:
        test_stock_positions()
        test_options_positions()
        test_mixed_positions()
        test_convenience_function()
        
        print("="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

