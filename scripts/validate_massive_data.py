#!/usr/bin/env python3
"""
Validate Massive (formerly Polygon) Data Collection
Tests that options data is actually being collected correctly
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from services.polygon_options_feed import MassiveOptionsFeed
from config import Config
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_massive_data():
    """Validate that Massive is collecting data correctly"""
    print("="*80)
    print("MASSIVE DATA COLLECTION VALIDATION")
    print("="*80)
    print(f"Test Time: {datetime.now()}\n")
    
    # Initialize feed
    feed = MassiveOptionsFeed()
    
    if not feed.is_available():
        print("❌ Massive API key not configured")
        print()
        print("Please set one of these in .env:")
        print("  MASSIVE_API_KEY=your_key_here")
        print("  (or POLYGON_API_KEY=your_key_here for backwards compatibility)")
        print()
        return False
    
    print("✅ Massive API key configured")
    print()
    
    # Test symbol
    test_symbols = ["NVDA", "AAPL", "TSLA"]
    
    all_results = {}
    
    for symbol in test_symbols:
        print("="*80)
        print(f"Testing {symbol}")
        print("="*80)
        
        results = {
            'symbol': symbol,
            'expirations_found': False,
            'chain_found': False,
            'contract_count': 0,
            'expiration_count': 0,
            'sample_contract': None,
            'errors': []
        }
        
        # Test 1: Expiration dates
        try:
            print(f"\n1. Getting expiration dates for {symbol}...")
            expirations = feed.get_expiration_dates(symbol)
            
            if expirations:
                results['expirations_found'] = True
                results['expiration_count'] = len(expirations)
                print(f"   ✅ Found {len(expirations)} expiration dates")
                
                # Filter to 0-30 DTE range (user requirement)
                today = datetime.now().date()
                valid_expirations = []
                for exp_str in expirations:
                    try:
                        exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
                        dte = (exp_date - today).days
                        if 0 <= dte <= 30:
                            valid_expirations.append((exp_str, dte))
                    except:
                        continue
                
                print(f"   ✅ Found {len(valid_expirations)} expirations in 0-30 DTE range:")
                for exp_str, dte in valid_expirations[:5]:
                    print(f"      - {exp_str} ({dte} DTE)")
            else:
                results['errors'].append("No expiration dates found")
                print(f"   ❌ No expiration dates found")
        except Exception as e:
            results['errors'].append(f"Error getting expirations: {e}")
            print(f"   ❌ Error: {e}")
        
        # Test 2: Options chain
        try:
            print(f"\n2. Getting options chain for {symbol}...")
            chain = feed.get_options_chain(symbol)
            
            if chain:
                results['chain_found'] = True
                results['contract_count'] = len(chain)
                print(f"   ✅ Retrieved {len(chain)} option contracts")
                
                if chain:
                    sample = chain[0]
                    results['sample_contract'] = {
                        'ticker': sample.get('ticker', 'N/A'),
                        'strike': sample.get('strike_price', 'N/A'),
                        'expiration': sample.get('expiration_date', 'N/A'),
                        'type': sample.get('contract_type', 'N/A'),
                        'iv': sample.get('implied_volatility', 'N/A')
                    }
                    
                    print(f"   ✅ Sample contract:")
                    print(f"      Ticker: {sample.get('ticker', 'N/A')}")
                    print(f"      Strike: ${sample.get('strike_price', 'N/A')}")
                    print(f"      Expiration: {sample.get('expiration_date', 'N/A')}")
                    print(f"      Type: {sample.get('contract_type', 'N/A')}")
                    print(f"      IV: {sample.get('implied_volatility', 'N/A')}")
            else:
                results['errors'].append("No options chain data")
                print(f"   ❌ No options chain data retrieved")
        except Exception as e:
            results['errors'].append(f"Error getting chain: {e}")
            print(f"   ❌ Error: {e}")
        
        # Test 3: ATM option (if we have expirations)
        if results['expirations_found'] and expirations:
            try:
                print(f"\n3. Getting ATM call option...")
                expiration = expirations[0]
                atm_option = feed.get_atm_options(symbol, expiration, 'call')
                
                if atm_option:
                    print(f"   ✅ Found ATM option:")
                    print(f"      Strike: ${atm_option.get('strike_price', 'N/A')}")
                    print(f"      Expiration: {atm_option.get('expiration_date', 'N/A')}")
                    print(f"      Ticker: {atm_option.get('ticker', 'N/A')}")
                else:
                    print(f"   ⚠️  Could not find ATM option")
            except Exception as e:
                print(f"   ⚠️  Error getting ATM option: {e}")
        
        all_results[symbol] = results
        print()
    
    # Summary
    print("="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    all_good = True
    for symbol, results in all_results.items():
        status = "✅" if (results['expirations_found'] and results['chain_found']) else "❌"
        print(f"\n{symbol}:")
        print(f"  {status} Expirations: {results['expiration_count']} found")
        print(f"  {status} Options Chain: {results['contract_count']} contracts")
        
        if results['errors']:
            print(f"  ⚠️  Errors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"      - {error}")
            all_good = False
        
        if not (results['expirations_found'] and results['chain_found']):
            all_good = False
    
    print("\n" + "="*80)
    if all_good:
        print("✅ ALL TESTS PASSED - Massive data collection is working!")
        print("\nData Collection Status:")
        total_contracts = sum(r['contract_count'] for r in all_results.values())
        total_expirations = sum(r['expiration_count'] for r in all_results.values())
        print(f"  - Total contracts retrieved: {total_contracts}")
        print(f"  - Total expiration dates: {total_expirations}")
        print(f"  - Symbols tested: {len(all_results)}")
        return True
    else:
        print("❌ SOME TESTS FAILED - Review errors above")
        return False

if __name__ == "__main__":
    success = validate_massive_data()
    sys.exit(0 if success else 1)




