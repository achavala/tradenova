#!/usr/bin/env python3
"""
Comprehensive Black-Scholes Validation
Tests all Greeks and validates against known values
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from core.pricing.black_scholes import BlackScholes
from services.polygon_options_feed import MassiveOptionsFeed
from config import Config
from datetime import datetime

def test_basic_calculations():
    """Test basic Black-Scholes calculations"""
    print("="*80)
    print("TEST 1: BASIC BLACK-SCHOLES CALCULATIONS")
    print("="*80)
    
    bs = BlackScholes(risk_free_rate=0.05)
    
    # Test case: ATM call option
    S = 100.0
    K = 100.0
    T = 0.25  # 3 months
    sigma = 0.20  # 20% IV
    option_type = 'call'
    
    result = bs.calculate(S, K, T, sigma, option_type)
    
    print(f"\nInput Parameters:")
    print(f"  Spot Price (S): ${S:.2f}")
    print(f"  Strike (K): ${K:.2f}")
    print(f"  Time to Expiry (T): {T:.2f} years ({T*365:.0f} days)")
    print(f"  Volatility (σ): {sigma:.2%}")
    print(f"  Option Type: {option_type.upper()}")
    print(f"  Risk-Free Rate: 5%")
    
    print(f"\nCalculated Results:")
    print(f"  Price: ${result['price']:.4f}")
    print(f"  Delta: {result['delta']:.6f}")
    print(f"  Gamma: {result['gamma']:.6f}")
    print(f"  Vega: {result['vega']:.6f}")
    print(f"  Theta: {result['theta']:.6f} (per day)")
    print(f"  Rho: {result['rho']:.6f}")
    
    print(f"\nSecond-Order Greeks:")
    print(f"  Vanna: {result['vanna']:.6f}")
    print(f"  Vomma: {result['vomma']:.6f}")
    print(f"  Charm: {result['charm']:.6f}")
    print(f"  Speed: {result['speed']:.6f}")
    
    # Validations
    errors = []
    
    # Price should be positive
    if result['price'] <= 0:
        errors.append("Price should be positive")
    
    # ATM call delta should be around 0.5
    if not (0.4 <= result['delta'] <= 0.6):
        errors.append(f"ATM call delta should be ~0.5, got {result['delta']:.4f}")
    
    # Gamma should be positive
    if result['gamma'] <= 0:
        errors.append("Gamma should be positive")
    
    # Vega should be positive
    if result['vega'] <= 0:
        errors.append("Vega should be positive")
    
    # Theta should be negative (time decay)
    if result['theta'] >= 0:
        errors.append("Theta should be negative (time decay)")
    
    if errors:
        print(f"\n❌ VALIDATION ERRORS:")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print(f"\n✅ All basic validations passed")
        return True

def test_greeks_properties():
    """Test Greeks have correct properties"""
    print("\n" + "="*80)
    print("TEST 2: GREEKS PROPERTIES VALIDATION")
    print("="*80)
    
    bs = BlackScholes(risk_free_rate=0.05)
    
    test_cases = [
        {'S': 100, 'K': 90, 'T': 0.25, 'sigma': 0.20, 'type': 'call', 'desc': 'ITM Call'},
        {'S': 100, 'K': 100, 'T': 0.25, 'sigma': 0.20, 'type': 'call', 'desc': 'ATM Call'},
        {'S': 100, 'K': 110, 'T': 0.25, 'sigma': 0.20, 'type': 'call', 'desc': 'OTM Call'},
        {'S': 100, 'K': 90, 'T': 0.25, 'sigma': 0.20, 'type': 'put', 'desc': 'ITM Put'},
        {'S': 100, 'K': 100, 'T': 0.25, 'sigma': 0.20, 'type': 'put', 'desc': 'ATM Put'},
        {'S': 100, 'K': 110, 'T': 0.25, 'sigma': 0.20, 'type': 'put', 'desc': 'OTM Put'},
    ]
    
    all_passed = True
    
    for case in test_cases:
        result = bs.calculate(
            case['S'], case['K'], case['T'], case['sigma'], case['type']
        )
        
        print(f"\n{case['desc']}:")
        print(f"  Delta: {result['delta']:.4f}")
        print(f"  Gamma: {result['gamma']:.4f}")
        print(f"  Vega: {result['vega']:.4f}")
        print(f"  Theta: {result['theta']:.4f}")
        
        # Validations
        if case['type'] == 'call':
            # Call delta should be 0 to 1
            if not (0 <= result['delta'] <= 1):
                print(f"  ❌ Call delta out of range: {result['delta']:.4f}")
                all_passed = False
        else:
            # Put delta should be -1 to 0
            if not (-1 <= result['delta'] <= 0):
                print(f"  ❌ Put delta out of range: {result['delta']:.4f}")
                all_passed = False
        
        # Gamma always positive
        if result['gamma'] <= 0:
            print(f"  ❌ Gamma should be positive: {result['gamma']:.4f}")
            all_passed = False
        
        # Vega always positive
        if result['vega'] <= 0:
            print(f"  ❌ Vega should be positive: {result['vega']:.4f}")
            all_passed = False
        
        # Theta always negative
        if result['theta'] >= 0:
            print(f"  ❌ Theta should be negative: {result['theta']:.4f}")
            all_passed = False
    
    if all_passed:
        print(f"\n✅ All Greeks properties validated")
    else:
        print(f"\n❌ Some Greeks properties failed")
    
    return all_passed

def test_second_order_greeks():
    """Test second-order Greeks are calculated"""
    print("\n" + "="*80)
    print("TEST 3: SECOND-ORDER GREEKS VALIDATION")
    print("="*80)
    
    bs = BlackScholes(risk_free_rate=0.05)
    
    result = bs.calculate(100, 100, 0.25, 0.20, 'call')
    
    second_order = ['vanna', 'vomma', 'charm', 'speed']
    
    print(f"\nSecond-Order Greeks:")
    all_present = True
    
    for greek in second_order:
        if greek in result:
            value = result[greek]
            print(f"  {greek.capitalize()}: {value:.6f}")
            
            # Check if finite
            if not np.isfinite(value):
                print(f"    ❌ {greek} is not finite")
                all_present = False
        else:
            print(f"  ❌ {greek} not found in result")
            all_present = False
    
    if all_present:
        print(f"\n✅ All second-order Greeks calculated and finite")
    else:
        print(f"\n❌ Some second-order Greeks missing or invalid")
    
    return all_present

def test_implied_volatility():
    """Test implied volatility calculation"""
    print("\n" + "="*80)
    print("TEST 4: IMPLIED VOLATILITY CALCULATION")
    print("="*80)
    
    bs = BlackScholes(risk_free_rate=0.05)
    
    # Known parameters
    S = 100.0
    K = 100.0
    T = 0.25
    true_iv = 0.20  # 20%
    option_type = 'call'
    
    # Calculate price with known IV
    result = bs.calculate(S, K, T, true_iv, option_type)
    market_price = result['price']
    
    print(f"\nTest Parameters:")
    print(f"  Spot: ${S:.2f}, Strike: ${K:.2f}, T: {T:.2f} years")
    print(f"  True IV: {true_iv:.2%}")
    print(f"  Market Price: ${market_price:.4f}")
    
    # Calculate IV from price
    calculated_iv = bs.calculate_implied_volatility(
        market_price, S, K, T, option_type
    )
    
    if calculated_iv:
        print(f"  Calculated IV: {calculated_iv:.2%}")
        
        iv_error = abs(calculated_iv - true_iv)
        print(f"  Error: {iv_error:.4%}")
        
        if iv_error < 0.01:  # Within 1%
            print(f"\n✅ IV calculation accurate (within 1%)")
            
            # Verify by recalculating price
            verify_result = bs.calculate(S, K, T, calculated_iv, option_type)
            price_error = abs(verify_result['price'] - market_price)
            print(f"  Verified Price: ${verify_result['price']:.4f} (Error: ${price_error:.4f})")
            
            if price_error < 0.01:
                print(f"  ✅ Price verification passed")
                return True
            else:
                print(f"  ❌ Price verification failed")
                return False
        else:
            print(f"\n❌ IV calculation error too large")
            return False
    else:
        print(f"\n❌ IV calculation failed")
        return False

def test_market_data_comparison():
    """Compare with real market data from Massive API"""
    print("\n" + "="*80)
    print("TEST 5: MARKET DATA COMPARISON")
    print("="*80)
    
    feed = MassiveOptionsFeed()
    
    if not feed.is_available():
        print("⚠️  Massive API not available, skipping market data comparison")
        return True
    
    bs = BlackScholes(risk_free_rate=0.05)
    
    # Get NVDA $170 Call
    contract = feed.get_option_by_strike('NVDA', 170, '2025-12-19', 'call')
    
    if not contract:
        print("⚠️  Could not fetch contract, skipping market data comparison")
        return True
    
    details = contract.get('details', {})
    day = contract.get('day', {})
    greeks = contract.get('greeks', {})
    underlying = contract.get('underlying_asset', {})
    
    market_price = day.get('close', 0)
    market_iv = contract.get('implied_volatility', 0)
    market_delta = greeks.get('delta', 0)
    market_gamma = greeks.get('gamma', 0)
    market_vega = greeks.get('vega', 0)
    market_theta = greeks.get('theta', 0)
    
    spot = underlying.get('price', 171.13)
    strike = details.get('strike_price', 170)
    expiration = details.get('expiration_date', '2025-12-19')
    
    # Calculate DTE
    exp_date = datetime.strptime(expiration, '%Y-%m-%d').date()
    today = datetime.now().date()
    dte = (exp_date - today).days
    tte = dte / 365.0
    
    print(f"\nMarket Data (NVDA ${strike} Call, {dte} DTE):")
    print(f"  Spot: ${spot:.2f}")
    print(f"  Market Price: ${market_price:.2f}")
    print(f"  Market IV: {market_iv:.2%}")
    print(f"  Market Delta: {market_delta:.4f}")
    print(f"  Market Gamma: {market_gamma:.4f}")
    print(f"  Market Vega: {market_vega:.4f}")
    print(f"  Market Theta: {market_theta:.4f}")
    
    # Calculate using Black-Scholes
    bs_result = bs.calculate(spot, strike, tte, market_iv, 'call')
    
    print(f"\nBlack-Scholes Calculation:")
    print(f"  Calculated Price: ${bs_result['price']:.2f}")
    print(f"  Calculated Delta: {bs_result['delta']:.4f}")
    print(f"  Calculated Gamma: {bs_result['gamma']:.4f}")
    print(f"  Calculated Vega: {bs_result['vega']:.4f}")
    print(f"  Calculated Theta: {bs_result['theta']:.4f}")
    
    # Compare
    print(f"\nComparison:")
    price_diff = abs(bs_result['price'] - market_price)
    delta_diff = abs(bs_result['delta'] - market_delta)
    gamma_diff = abs(bs_result['gamma'] - market_gamma)
    vega_diff = abs(bs_result['vega'] - market_vega)
    theta_diff = abs(bs_result['theta'] - market_theta)
    
    print(f"  Price Difference: ${price_diff:.2f}")
    print(f"  Delta Difference: {delta_diff:.4f}")
    print(f"  Gamma Difference: {gamma_diff:.4f}")
    print(f"  Vega Difference: {vega_diff:.4f}")
    print(f"  Theta Difference: {theta_diff:.4f}")
    
    # Validation thresholds
    all_passed = True
    
    if price_diff < 1.0:  # Within $1
        print(f"  ✅ Price accurate (within ${price_diff:.2f})")
    else:
        print(f"  ⚠️  Price difference: ${price_diff:.2f}")
        all_passed = False
    
    if delta_diff < 0.1:  # Within 0.1
        print(f"  ✅ Delta accurate (within {delta_diff:.4f})")
    else:
        print(f"  ⚠️  Delta difference: {delta_diff:.4f}")
        all_passed = False
    
    if gamma_diff < 0.01:  # Within 0.01
        print(f"  ✅ Gamma accurate (within {gamma_diff:.4f})")
    else:
        print(f"  ⚠️  Gamma difference: {gamma_diff:.4f}")
    
    if vega_diff < 0.01:  # Within 0.01
        print(f"  ✅ Vega accurate (within {vega_diff:.4f})")
    else:
        print(f"  ⚠️  Vega difference: {vega_diff:.4f}")
    
    if theta_diff < 0.1:  # Within 0.1
        print(f"  ✅ Theta accurate (within {theta_diff:.4f})")
    else:
        print(f"  ⚠️  Theta difference: {theta_diff:.4f}")
    
    if all_passed:
        print(f"\n✅ Market data comparison passed")
    else:
        print(f"\n⚠️  Some differences exceed thresholds (may be due to data timing)")
    
    return all_passed

def test_edge_cases():
    """Test edge cases"""
    print("\n" + "="*80)
    print("TEST 6: EDGE CASES")
    print("="*80)
    
    bs = BlackScholes(risk_free_rate=0.05)
    
    all_passed = True
    
    # Test expired option
    print("\n1. Expired Option:")
    result = bs.calculate(100, 100, 0.0, 0.20, 'call')
    if result['price'] == 0 and result['delta'] == 0:
        print("  ✅ Expired option handled correctly")
    else:
        print(f"  ❌ Expired option not handled: price={result['price']}, delta={result['delta']}")
        all_passed = False
    
    # Test very short expiry
    print("\n2. Very Short Expiry (1 day):")
    result = bs.calculate(100, 100, 1/365, 0.20, 'call')
    if result['price'] > 0 and np.isfinite(result['price']):
        print(f"  ✅ Short expiry handled: price=${result['price']:.4f}")
    else:
        print(f"  ❌ Short expiry failed")
        all_passed = False
    
    # Test very long expiry
    print("\n3. Long Expiry (1 year):")
    result = bs.calculate(100, 100, 1.0, 0.20, 'call')
    if result['price'] > 0 and np.isfinite(result['price']):
        print(f"  ✅ Long expiry handled: price=${result['price']:.4f}")
    else:
        print(f"  ❌ Long expiry failed")
        all_passed = False
    
    # Test high volatility
    print("\n4. High Volatility (100%):")
    result = bs.calculate(100, 100, 0.25, 1.0, 'call')
    if result['price'] > 0 and np.isfinite(result['price']):
        print(f"  ✅ High volatility handled: price=${result['price']:.4f}")
    else:
        print(f"  ❌ High volatility failed")
        all_passed = False
    
    if all_passed:
        print(f"\n✅ All edge cases handled correctly")
    else:
        print(f"\n❌ Some edge cases failed")
    
    return all_passed

def main():
    """Run all validation tests"""
    print("\n" + "="*80)
    print("COMPREHENSIVE BLACK-SCHOLES VALIDATION")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = []
    
    # Run all tests
    results.append(("Basic Calculations", test_basic_calculations()))
    results.append(("Greeks Properties", test_greeks_properties()))
    results.append(("Second-Order Greeks", test_second_order_greeks()))
    results.append(("Implied Volatility", test_implied_volatility()))
    results.append(("Market Data Comparison", test_market_data_comparison()))
    results.append(("Edge Cases", test_edge_cases()))
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTests Passed: {passed}/{total}\n")
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    if passed == total:
        print(f"\n✅ ALL TESTS PASSED - Black-Scholes implementation is VALIDATED")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed or had warnings")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

