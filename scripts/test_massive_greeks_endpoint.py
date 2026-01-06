#!/usr/bin/env python3
"""
Test Massive API endpoints for Greeks data
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import json
import requests
from config import Config

def test_greeks_endpoints():
    """Test different endpoints to get Greeks"""
    
    api_key = Config.MASSIVE_API_KEY or os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ API key not configured")
        return
    
    # Test with a specific option ticker
    option_ticker = "O:NVDA251219C00171000"  # NVDA Dec 19 call at $171 strike
    symbol = "NVDA"
    
    print(f"Testing Greeks endpoints for {symbol}")
    print("="*80)
    
    # Test 1: Previous close endpoint (might have Greeks)
    print("\n1. Testing /v2/aggs/ticker/{ticker}/prev endpoint:")
    url1 = f"https://api.polygon.io/v2/aggs/ticker/{option_ticker}/prev"
    params1 = {'apiKey': api_key}
    
    try:
        r1 = requests.get(url1, params=params1, timeout=30)
        if r1.status_code == 200:
            data1 = r1.json()
            print(f"✅ Status: {data1.get('status')}")
            if data1.get('results'):
                print(json.dumps(data1['results'][0], indent=2))
        else:
            print(f"❌ Status {r1.status_code}: {r1.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Try to get quotes endpoint
    print("\n2. Testing /v3/quotes/{ticker} endpoint:")
    url2 = f"https://api.polygon.io/v3/quotes/{option_ticker}"
    params2 = {'apiKey': api_key, 'limit': 1}
    
    try:
        r2 = requests.get(url2, params=params2, timeout=30)
        if r2.status_code == 200:
            data2 = r2.json()
            print(f"✅ Status: {data2.get('status')}")
            if data2.get('results'):
                print(json.dumps(data2['results'][0], indent=2))
        else:
            print(f"❌ Status {r2.status_code}: {r2.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Get contracts first, then request specific ones
    print("\n3. Getting contracts near current price:")
    url3 = f"https://api.polygon.io/v3/reference/options/contracts"
    params3 = {
        'underlying_ticker': symbol,
        'strike_price.gte': 150,  # Minimum strike
        'strike_price.lte': 200,  # Maximum strike
        'expiration_date': '2025-12-19',
        'contract_type': 'call',
        'limit': 50,
        'apiKey': api_key
    }
    
    try:
        r3 = requests.get(url3, params=params3, timeout=30)
        if r3.status_code == 200:
            data3 = r3.json()
            print(f"✅ Status: {data3.get('status')}")
            results = data3.get('results', [])
            print(f"✅ Found {len(results)} contracts with strikes 150-200")
            
            if results:
                print("\nSample contracts:")
                for i, contract in enumerate(results[:5]):
                    print(f"  {i+1}. Strike: ${contract.get('strike_price')}, Ticker: {contract.get('ticker')}")
        else:
            print(f"❌ Status {r3.status_code}: {r3.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Try snapshot with specific tickers
    print("\n4. Testing snapshot with specific ticker filter:")
    url4 = f"https://api.polygon.io/v3/snapshot/options/{symbol}"
    params4 = {
        'strike_price': 171,
        'expiration_date': '2025-12-19',
        'contract_type': 'call',
        'apiKey': api_key
    }
    
    try:
        r4 = requests.get(url4, params=params4, timeout=30)
        if r4.status_code == 200:
            data4 = r4.json()
            print(f"✅ Status: {data4.get('status')}")
            results = data4.get('results', [])
            print(f"✅ Found {len(results)} contracts")
            if results:
                print("\nFirst result with Greeks:")
                print(json.dumps(results[0], indent=2))
        else:
            print(f"❌ Status {r4.status_code}: {r4.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_greeks_endpoints()




