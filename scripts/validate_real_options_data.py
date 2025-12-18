#!/usr/bin/env python3
"""
Validate REAL options data from Massive - with correct prices, Greeks, premiums
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from services.polygon_options_feed import MassiveOptionsFeed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_real_data():
    """Validate that we're getting REAL options data"""
    
    feed = MassiveOptionsFeed()
    
    if not feed.is_available():
        print("❌ Massive API key not configured")
        print("   Set MASSIVE_API_KEY or POLYGON_API_KEY in .env")
        return False
    
    print("="*80)
    print("VALIDATING REAL OPTIONS DATA FROM MASSIVE")
    print("="*80)
    print()
    
    test_symbols = ["NVDA", "AAPL", "TSLA"]
    
    for symbol in test_symbols:
        print(f"Testing {symbol}:")
        print("-" * 80)
        
        # Test 1: Get current price
        current_price = feed._get_current_stock_price(symbol)
        if current_price:
            print(f"✅ Current {symbol} Price: ${current_price:.2f}")
        else:
            print(f"⚠️  Could not get current price for {symbol}")
            continue
        
        # Test 2: Get options chain with real data
        print(f"\n2. Getting options chain (near ATM, Dec 19 expiration)...")
        chain = feed.get_options_chain(
            symbol,
            expiration_date='2025-12-19',
            strike_min=current_price * 0.8,  # 20% OTM
            strike_max=current_price * 1.2,  # 20% ITM
            current_price=current_price
        )
        
        if not chain:
            print(f"   ❌ No options chain data")
            continue
        
        print(f"   ✅ Retrieved {len(chain)} contracts")
        
        # Test 3: Validate first few contracts have REAL data
        print(f"\n3. Validating contract data:")
        valid_contracts = 0
        
        for i, contract in enumerate(chain[:5]):
            details = contract.get('details', {})
            day = contract.get('day', {})
            greeks = contract.get('greeks', {})
            
            ticker = details.get('ticker', 'N/A')
            strike = details.get('strike_price', 0)
            expiration = details.get('expiration_date', 'N/A')
            last_price = day.get('close', 0)
            volume = day.get('volume', 0)
            
            # Validate strike is reasonable (not $0.5 or $5)
            is_valid = strike > current_price * 0.5 and strike < current_price * 1.5
            
            status = "✅" if is_valid else "❌"
            print(f"\n   Contract {i+1}: {status}")
            print(f"     Ticker: {ticker}")
            print(f"     Strike: ${strike:.2f} {'(VALID)' if is_valid else '(INVALID - too low!)'}")
            print(f"     Last Price: ${last_price:.2f}")
            print(f"     Volume: {volume:,}")
            print(f"     Expiration: {expiration}")
            
            if greeks:
                print(f"     Greeks: ✅")
                print(f"       Delta: {greeks.get('delta', 'N/A'):.4f}" if greeks.get('delta') else "       Delta: N/A")
                print(f"       Gamma: {greeks.get('gamma', 'N/A'):.4f}" if greeks.get('gamma') else "       Gamma: N/A")
                print(f"       Theta: {greeks.get('theta', 'N/A'):.4f}" if greeks.get('theta') else "       Theta: N/A")
                print(f"       Vega: {greeks.get('vega', 'N/A'):.4f}" if greeks.get('vega') else "       Vega: N/A")
                print(f"     IV: {contract.get('implied_volatility', 'N/A'):.2%}" if contract.get('implied_volatility') else "     IV: N/A")
            else:
                print(f"     Greeks: ❌ Not available")
            
            if is_valid:
                valid_contracts += 1
        
        # Test 4: Get ATM option
        print(f"\n4. Getting ATM call option...")
        atm_call = feed.get_atm_options(symbol, '2025-12-19', 'call', current_price)
        
        if atm_call:
            details = atm_call.get('details', {})
            strike = details.get('strike_price', 0)
            day = atm_call.get('day', {})
            greeks = atm_call.get('greeks', {})
            
            print(f"   ✅ Found ATM call:")
            print(f"     Ticker: {details.get('ticker', 'N/A')}")
            print(f"     Strike: ${strike:.2f} (vs current ${current_price:.2f})")
            print(f"     Last Price: ${day.get('close', 0):.2f}")
            print(f"     Volume: {day.get('volume', 0):,}")
            
            if greeks:
                print(f"     Delta: {greeks.get('delta', 'N/A'):.4f}")
                print(f"     Gamma: {greeks.get('gamma', 'N/A'):.4f}")
                print(f"     Theta: {greeks.get('theta', 'N/A'):.4f}")
                print(f"     Vega: {greeks.get('vega', 'N/A'):.4f}")
                print(f"     IV: {atm_call.get('implied_volatility', 'N/A'):.2%}")
        else:
            print(f"   ❌ Could not find ATM option")
        
        print()
    
    print("="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
    
    return True

if __name__ == "__main__":
    success = validate_real_data()
    sys.exit(0 if success else 1)

