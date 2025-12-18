#!/usr/bin/env python3
"""
Debug Massive API Response - See exactly what data we're getting
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import json
import requests
from datetime import datetime
from config import Config

def debug_api_response():
    """Debug the actual API response from Massive"""
    
    api_key = Config.MASSIVE_API_KEY or os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ API key not configured")
        return
    
    symbol = "NVDA"
    print(f"Testing Massive API for {symbol}")
    print("="*80)
    
    # Test 1: Options Contracts endpoint
    print("\n1. Testing /v3/reference/options/contracts endpoint:")
    print("-" * 80)
    
    url = "https://api.polygon.io/v3/reference/options/contracts"
    params = {
        'underlying_ticker': symbol,
        'limit': 10,  # Just get 10 contracts
        'apiKey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nResponse Status: {data.get('status')}")
            print(f"Results Count: {len(data.get('results', []))}")
            
            if data.get('results'):
                print("\nFIRST CONTRACT (Full JSON):")
                print(json.dumps(data['results'][0], indent=2))
                
                print("\nALL CONTRACTS (Key Fields):")
                for i, contract in enumerate(data['results'][:5]):
                    print(f"\nContract {i+1}:")
                    print(f"  Keys: {list(contract.keys())}")
                    for key in ['ticker', 'contract_type', 'exercise_style', 'expiration_date', 
                               'shares_per_contract', 'cfi', 'strike_price', 'ticker_root']:
                        if key in contract:
                            print(f"  {key}: {contract[key]}")
        else:
            print(f"Error Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Options Snapshot endpoint (for current prices)
    print("\n\n2. Testing /v3/snapshot/options endpoint (for quotes/prices):")
    print("-" * 80)
    
    url2 = "https://api.polygon.io/v3/snapshot/options/" + symbol
    params2 = {
        'apiKey': api_key
    }
    
    try:
        response2 = requests.get(url2, params=params2, timeout=30)
        print(f"Status Code: {response2.status_code}")
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"\nResponse Status: {data2.get('status')}")
            
            if 'results' in data2 and data2['results']:
                print(f"Results Count: {len(data2['results'])}")
                print("\nFIRST OPTION SNAPSHOT (Full JSON):")
                print(json.dumps(data2['results'][0], indent=2))
            else:
                print("No results in snapshot")
                print(f"Full Response: {json.dumps(data2, indent=2)}")
        else:
            print(f"Error Response: {response2.text}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Try to parse strike from ticker
    print("\n\n3. Parsing strike price from ticker format:")
    print("-" * 80)
    
    test_tickers = [
        "O:NVDA251219C00000500",
        "O:NVDA251219C00083000",
        "O:AAPL251219C00005000",
        "O:AAPL251219C00237500"
    ]
    
    for ticker in test_tickers:
        print(f"\nTicker: {ticker}")
        # Polygon ticker format: O:SYMBOL{YY}{MM}{DD}{C/P}{STRIKE}
        # Example: O:NVDA251219C00083000 = NVDA, Dec 19 2025, Call, Strike 83000 (divide by 1000 = $83)
        try:
            parts = ticker.split(':')
            if len(parts) == 2:
                option_part = parts[1]
                # Extract strike (last part before C/P, then divide by 1000)
                # Format: SYMBOL + YYMMDD + C/P + STRIKE (8 digits)
                symbol_part = option_part[:4]  # NVDA
                date_part = option_part[4:10]  # 251219
                cp_part = option_part[10]      # C or P
                strike_part = option_part[11:] # 00000500 or 00083000
                
                strike_price = float(strike_part) / 1000.0
                
                print(f"  Symbol: {symbol_part}")
                print(f"  Date: {date_part}")
                print(f"  Type: {cp_part}")
                print(f"  Strike (raw): {strike_part}")
                print(f"  Strike (parsed): ${strike_price}")
        except Exception as e:
            print(f"  Error parsing: {e}")

if __name__ == "__main__":
    debug_api_response()

