#!/usr/bin/env python3
"""
Test /v2/options/quotes/latest endpoint directly
"""
import sys
import json
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from alpaca_client import AlpacaClient
from config import Config

def test_nbbo_endpoint():
    """Test the NBBO options quotes endpoint"""
    print("="*80)
    print("🧪 Testing /v2/options/quotes/latest Endpoint")
    print("="*80)
    print()
    
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    # Test with a known option symbol
    test_symbol = "NVDA251212C00185000"  # NVDA Dec 12 2025 $185 Call
    
    print(f"Testing symbol: {test_symbol}")
    print()
    
    try:
        url = f"{client.ALPACA_BASE_URL}/v2/options/quotes/latest"
        api_key = getattr(client.api, '_key_id', '')
        secret_key = getattr(client.api, '_secret_key', '')
        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key
        }
        params = {
            "symbols": test_symbol
        }
        
        print(f"URL: {url}")
        print(f"Params: {params}")
        print()
        
        response = requests.get(url, headers=headers, params=params)
        print(f"Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Response received:")
            print(json.dumps(data, indent=2))
            print()
            
            # Check structure
            if isinstance(data, dict):
                quotes = data.get('quotes', data.get('data', data.get('option_quotes', [])))
                if quotes:
                    print(f"Found {len(quotes)} quote(s)")
                    for i, q in enumerate(quotes, 1):
                        print(f"\nQuote #{i}:")
                        print(f"  Keys: {list(q.keys())}")
                        for key, value in q.items():
                            print(f"  {key}: {value}")
                else:
                    print("⚠️  No quotes in response")
                    print(f"  Top-level keys: {list(data.keys())}")
            else:
                print(f"⚠️  Unexpected response type: {type(data)}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_nbbo_endpoint()

