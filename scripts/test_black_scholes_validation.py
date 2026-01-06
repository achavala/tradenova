#!/usr/bin/env python3
"""
Validate Black-Scholes calculations against known values
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pricing.black_scholes import BlackScholes
from services.polygon_options_feed import MassiveOptionsFeed
from config import Config

def validate_black_scholes():
    """Validate Black-Scholes against real market data"""
    
    print("="*80)
    print("BLACK-SCHOLES VALIDATION")
    print("="*80)
    print()
    
    bs = BlackScholes(risk_free_rate=0.05)
    
    # Test 1: Basic calculation
    print("1. Basic Black-Scholes Calculation:")
    print("-" * 80)
    result = bs.calculate(
        spot_price=171.13,
        strike=170,
        time_to_expiry=2/365,  # 2 days
        volatility=0.4347,  # 43.47% IV
        option_type='call'
    )
    
    print(f"   Spot: $171.13, Strike: $170, DTE: 2, IV: 43.47%")
    print(f"   Price: ${result['price']:.2f}")
    print(f"   Delta: {result['delta']:.4f}")
    print(f"   Gamma: {result['gamma']:.4f}")
    print(f"   Vega: {result['vega']:.4f}")
    print(f"   Theta: {result['theta']:.4f}")
    print(f"   Vanna: {result['vanna']:.4f}")
    print(f"   Vomma: {result['vomma']:.4f}")
    print()
    
    # Test 2: Compare with Massive API data
    print("2. Comparing with Massive API Data (NVDA $170 Call):")
    print("-" * 80)
    
    feed = MassiveOptionsFeed()
    if feed.is_available():
        contract = feed.get_option_by_strike('NVDA', 170, '2025-12-19', 'call')
        
        if contract:
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
            from datetime import datetime
            exp_date = datetime.strptime(expiration, '%Y-%m-%d').date()
            today = datetime.now().date()
            dte = (exp_date - today).days
            tte = dte / 365.0
            
            print(f"   Market Data:")
            print(f"     Price: ${market_price:.2f}")
            print(f"     IV: {market_iv:.2%}")
            print(f"     Delta: {market_delta:.4f}")
            print(f"     Gamma: {market_gamma:.4f}")
            print(f"     Vega: {market_vega:.4f}")
            print(f"     Theta: {market_theta:.4f}")
            print()
            
            # Calculate using Black-Scholes
            bs_result = bs.calculate(
                spot_price=spot,
                strike=strike,
                time_to_expiry=tte,
                volatility=market_iv,
                option_type='call'
            )
            
            print(f"   Black-Scholes Calculation:")
            print(f"     Price: ${bs_result['price']:.2f} (Diff: ${abs(bs_result['price'] - market_price):.2f})")
            print(f"     Delta: {bs_result['delta']:.4f} (Diff: {abs(bs_result['delta'] - market_delta):.4f})")
            print(f"     Gamma: {bs_result['gamma']:.4f} (Diff: {abs(bs_result['gamma'] - market_gamma):.4f})")
            print(f"     Vega: {bs_result['vega']:.4f} (Diff: {abs(bs_result['vega'] - market_vega):.4f})")
            print(f"     Theta: {bs_result['theta']:.4f} (Diff: {abs(bs_result['theta'] - market_theta):.4f})")
            print()
            
            # Validate
            price_diff = abs(bs_result['price'] - market_price)
            delta_diff = abs(bs_result['delta'] - market_delta)
            
            if price_diff < 1.0:  # Within $1
                print(f"   ✅ Price calculation accurate (within ${price_diff:.2f})")
            else:
                print(f"   ⚠️  Price difference: ${price_diff:.2f}")
            
            if delta_diff < 0.1:  # Within 0.1
                print(f"   ✅ Delta calculation accurate (within {delta_diff:.4f})")
            else:
                print(f"   ⚠️  Delta difference: {delta_diff:.4f}")
        else:
            print("   ⚠️  Could not fetch contract from Massive")
    else:
        print("   ⚠️  Massive API not available")
    
    print()
    
    # Test 3: Implied Volatility calculation
    print("3. Implied Volatility Calculation:")
    print("-" * 80)
    
    # Use known price to calculate IV
    test_price = 3.00
    calculated_iv = bs.calculate_implied_volatility(
        market_price=test_price,
        spot_price=171.13,
        strike=170,
        time_to_expiry=2/365,
        option_type='call'
    )
    
    if calculated_iv:
        print(f"   Market Price: ${test_price:.2f}")
        print(f"   Calculated IV: {calculated_iv:.2%}")
        
        # Verify by calculating price with this IV
        verify_result = bs.calculate(171.13, 170, 2/365, calculated_iv, 'call')
        print(f"   Verified Price: ${verify_result['price']:.2f} (Diff: ${abs(verify_result['price'] - test_price):.2f})")
        
        if abs(verify_result['price'] - test_price) < 0.10:
            print(f"   ✅ IV calculation accurate")
        else:
            print(f"   ⚠️  IV calculation may need adjustment")
    else:
        print("   ❌ IV calculation failed")
    
    print()
    print("="*80)
    print("VALIDATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    validate_black_scholes()




