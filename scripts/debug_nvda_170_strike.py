#!/usr/bin/env python3
"""
Debug NVDA $170 Strike Call 12/19 - Compare with Webull/Robinhood
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import json
import requests
from datetime import datetime
from config import Config

def debug_nvda_170_strike():
    """Debug the exact NVDA $170 Call 12/19 contract"""
    
    api_key = Config.MASSIVE_API_KEY or os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ API key not configured")
        return
    
    print("="*80)
    print("DEBUGGING NVDA $170 CALL 12/19 - COMPARING WITH WEBULL/ROBINHOOD")
    print("="*80)
    print()
    
    # Expected values from Webull/Robinhood:
    print("📊 EXPECTED VALUES (from Webull/Robinhood):")
    print("  Strike: $170")
    print("  Expiration: 2025-12-19")
    print("  Last Price: ~$3.00 (Webull shows $3.00, Robinhood shows $3.00-$3.05)")
    print("  IV: ~48.78% (Webull) or 52.55% (Robinhood)")
    print("  Delta: ~0.6095 (Webull) or 0.5671 (Robinhood)")
    print("  Gamma: ~0.0643 (Webull) or 0.0620 (Robinhood)")
    print("  Theta: ~-0.7253 (Webull) or -0.6945 (Robinhood)")
    print("  Open Interest: 25,371")
    print()
    
    # Test 1: Get exact contract by ticker
    print("1. Getting exact contract by ticker: O:NVDA251219C00170000")
    print("-" * 80)
    
    ticker = "O:NVDA251219C00170000"  # NVDA Dec 19 2025 $170 Call
    
    # Try snapshot endpoint with specific ticker
    url = f"https://api.polygon.io/v3/snapshot/options/NVDA"
    params = {
        'strike_price': 170,
        'expiration_date': '2025-12-19',
        'contract_type': 'call',
        'apiKey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Status: {data.get('status')}")
            results = data.get('results', [])
            print(f"Results Count: {len(results)}")
            
            # Find the exact $170 strike
            target_contract = None
            for contract in results:
                details = contract.get('details', {})
                strike = details.get('strike_price', 0)
                if strike == 170:
                    target_contract = contract
                    break
            
            if target_contract:
                print("\n✅ FOUND $170 STRIKE CONTRACT:")
                print(json.dumps(target_contract, indent=2))
                
                details = target_contract.get('details', {})
                day = target_contract.get('day', {})
                greeks = target_contract.get('greeks', {})
                
                print("\n📊 EXTRACTED DATA:")
                print(f"  Ticker: {details.get('ticker', 'N/A')}")
                print(f"  Strike: ${details.get('strike_price', 'N/A')}")
                print(f"  Expiration: {details.get('expiration_date', 'N/A')}")
                print(f"  Last Price (close): ${day.get('close', 'N/A')}")
                print(f"  Open: ${day.get('open', 'N/A')}")
                print(f"  High: ${day.get('high', 'N/A')}")
                print(f"  Low: ${day.get('low', 'N/A')}")
                print(f"  Volume: {day.get('volume', 'N/A'):,}")
                print(f"  Open Interest: {target_contract.get('open_interest', 'N/A'):,}")
                print(f"  IV: {target_contract.get('implied_volatility', 'N/A'):.2%}" if target_contract.get('implied_volatility') else f"  IV: N/A")
                
                if greeks:
                    print(f"  Delta: {greeks.get('delta', 'N/A')}")
                    print(f"  Gamma: {greeks.get('gamma', 'N/A')}")
                    print(f"  Theta: {greeks.get('theta', 'N/A')}")
                    print(f"  Vega: {greeks.get('vega', 'N/A')}")
                else:
                    print("  Greeks: Not available")
                
                # Compare
                print("\n🔍 COMPARISON:")
                our_price = day.get('close', 0)
                expected_price = 3.00
                price_diff = abs(our_price - expected_price)
                print(f"  Price: ${our_price:.2f} vs Expected ~${expected_price:.2f} (Diff: ${price_diff:.2f})")
                
                if price_diff > 0.50:
                    print(f"  ❌ PRICE MISMATCH - Difference too large!")
                
                our_oi = target_contract.get('open_interest', 0)
                expected_oi = 25371
                oi_diff = abs(our_oi - expected_oi)
                print(f"  Open Interest: {our_oi:,} vs Expected {expected_oi:,} (Diff: {oi_diff:,})")
                
                if oi_diff > 1000:
                    print(f"  ❌ OPEN INTEREST MISMATCH - Difference too large!")
            else:
                print("❌ $170 strike contract not found in results")
                print("\nAvailable strikes:")
                for contract in results[:10]:
                    details = contract.get('details', {})
                    print(f"  - Strike: ${details.get('strike_price', 'N/A')}, Ticker: {details.get('ticker', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text[:500])
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Try getting quotes for specific ticker
    print("\n\n2. Trying quotes endpoint for specific ticker:")
    print("-" * 80)
    
    url2 = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
    params2 = {'apiKey': api_key}
    
    try:
        response2 = requests.get(url2, params=params2, timeout=30)
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"Status: {data2.get('status')}")
            if data2.get('results'):
                result = data2['results'][0]
                print(f"\nPrevious Close Data:")
                print(f"  Close: ${result.get('c', 'N/A')}")
                print(f"  Open: ${result.get('o', 'N/A')}")
                print(f"  High: ${result.get('h', 'N/A')}")
                print(f"  Low: ${result.get('l', 'N/A')}")
                print(f"  Volume: {result.get('v', 'N/A'):,}")
                print(f"  VWAP: ${result.get('vw', 'N/A')}")
        else:
            print(f"Status {response2.status_code}: {response2.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Check if we need real-time vs delayed data
    print("\n\n3. Checking data timing (real-time vs delayed):")
    print("-" * 80)
    
    # Check underlying asset timeframe
    url3 = f"https://api.polygon.io/v3/snapshot/options/NVDA"
    params3 = {
        'strike_price': 170,
        'expiration_date': '2025-12-19',
        'contract_type': 'call',
        'apiKey': api_key
    }
    
    try:
        response3 = requests.get(url3, params=params3, timeout=30)
        if response3.status_code == 200:
            data3 = response3.json()
            if data3.get('results'):
                underlying = data3['results'][0].get('underlying_asset', {})
                timeframe = underlying.get('timeframe', 'N/A')
                last_updated = underlying.get('last_updated', 'N/A')
                print(f"  Timeframe: {timeframe}")
                print(f"  Last Updated: {last_updated}")
                
                if timeframe == 'DELAYED':
                    print("  ⚠️  Data is DELAYED - may explain price differences")
                elif timeframe == 'REAL-TIME':
                    print("  ✅ Data is REAL-TIME")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_nvda_170_strike()




