#!/usr/bin/env python3
"""
Validate EXACT strike prices match Webull/Robinhood
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from services.polygon_options_feed import MassiveOptionsFeed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_exact_strikes():
    """Validate exact strikes match broker data"""
    
    feed = MassiveOptionsFeed()
    
    if not feed.is_available():
        print("❌ Massive API key not configured")
        return False
    
    print("="*80)
    print("VALIDATING EXACT STRIKE PRICES vs WEBULL/ROBINHOOD")
    print("="*80)
    print()
    
    # Test cases from user's screenshots
    test_cases = [
        {
            'symbol': 'NVDA',
            'strike': 170,
            'expiration': '2025-12-19',
            'type': 'call',
            'expected_price': 3.00,
            'expected_oi': 25371,
            'expected_delta': 0.61,  # Webull: 0.6095, Robinhood: 0.5671
            'expected_iv': 0.49,  # Webull: 48.78%, Robinhood: 52.55%
        }
    ]
    
    all_passed = True
    
    for test in test_cases:
        print(f"Testing {test['symbol']} ${test['strike']} {test['type'].upper()} {test['expiration']}:")
        print("-" * 80)
        
        # Get exact contract
        contract = feed.get_option_by_strike(
            test['symbol'],
            test['strike'],
            test['expiration'],
            test['type']
        )
        
        if not contract:
            print(f"  ❌ Contract not found")
            all_passed = False
            continue
        
        details = contract.get('details', {})
        day = contract.get('day', {})
        greeks = contract.get('greeks', {})
        
        strike = details.get('strike_price', 0)
        price = day.get('close', 0)
        oi = contract.get('open_interest', 0)
        iv = contract.get('implied_volatility', 0)
        delta = greeks.get('delta', 0)
        
        print(f"  ✅ Contract found:")
        print(f"     Ticker: {details.get('ticker', 'N/A')}")
        print(f"     Strike: ${strike:.2f}")
        print(f"     Last Price: ${price:.2f}")
        print(f"     Open Interest: {oi:,}")
        print(f"     IV: {iv:.2%}")
        print(f"     Delta: {delta:.4f}")
        
        # Validate
        print(f"\n  📊 Validation:")
        
        # Price check
        price_diff = abs(price - test['expected_price'])
        if price_diff < 0.10:  # Within 10 cents
            print(f"     ✅ Price: ${price:.2f} (Expected ~${test['expected_price']:.2f}, Diff: ${price_diff:.2f})")
        else:
            print(f"     ❌ Price: ${price:.2f} (Expected ~${test['expected_price']:.2f}, Diff: ${price_diff:.2f})")
            all_passed = False
        
        # Open Interest check
        oi_diff = abs(oi - test['expected_oi'])
        if oi_diff < 100:  # Within 100 contracts
            print(f"     ✅ Open Interest: {oi:,} (Expected {test['expected_oi']:,}, Diff: {oi_diff:,})")
        else:
            print(f"     ⚠️  Open Interest: {oi:,} (Expected {test['expected_oi']:,}, Diff: {oi_diff:,})")
        
        # Delta check (allow some variance)
        delta_diff = abs(delta - test['expected_delta'])
        if delta_diff < 0.1:  # Within 0.1
            print(f"     ✅ Delta: {delta:.4f} (Expected ~{test['expected_delta']:.2f}, Diff: {delta_diff:.4f})")
        else:
            print(f"     ⚠️  Delta: {delta:.4f} (Expected ~{test['expected_delta']:.2f}, Diff: {delta_diff:.4f})")
        
        # IV check (allow some variance)
        iv_diff = abs(iv - test['expected_iv'])
        if iv_diff < 0.10:  # Within 10%
            print(f"     ✅ IV: {iv:.2%} (Expected ~{test['expected_iv']:.2%}, Diff: {iv_diff:.2%})")
        else:
            print(f"     ⚠️  IV: {iv:.2%} (Expected ~{test['expected_iv']:.2%}, Diff: {iv_diff:.2%})")
        
        print()
    
    print("="*80)
    if all_passed:
        print("✅ ALL VALIDATIONS PASSED")
    else:
        print("❌ SOME VALIDATIONS FAILED")
    print("="*80)
    
    return all_passed

if __name__ == "__main__":
    success = validate_exact_strikes()
    sys.exit(0 if success else 1)

