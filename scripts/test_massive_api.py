#!/usr/bin/env python3
"""
Test Massive API Connection
Quick test to verify API is working and see actual response format
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.massive_data_feed import MassiveDataFeed
from config import Config

def test_api():
    print("="*60)
    print("Massive API Connection Test")
    print("="*60)
    
    # Check API key
    if not Config.MASSIVE_API_KEY:
        print("❌ MASSIVE_API_KEY not set in .env")
        return 1
    
    print(f"✅ API Key: {Config.MASSIVE_API_KEY[:10]}...")
    
    # Initialize feed
    feed = MassiveDataFeed(Config.MASSIVE_API_KEY, Config.MASSIVE_BASE_URL)
    
    if not feed.is_available():
        print("❌ Massive API not available")
        return 1
    
    print("✅ Feed initialized")
    
    # Test 1: Get current options chain (no date)
    print("\n" + "-"*60)
    print("Test 1: Get current options chain for AAPL")
    print("-"*60)
    
    chain = feed.get_options_chain('AAPL', date=None)
    print(f"Contracts returned: {len(chain)}")
    
    if chain:
        print(f"\nFirst contract sample:")
        print(json.dumps(chain[0], indent=2))
    else:
        print("⚠️  No contracts returned")
        print("\nTesting raw API call...")
        
        # Make raw request to see response
        endpoint = "v3/snapshot/options/AAPL"
        response = feed._make_request(endpoint, {})
        
        if response:
            print(f"\nRaw API response:")
            print(f"Type: {type(response)}")
            if isinstance(response, dict):
                print(f"Keys: {list(response.keys())}")
                print(f"\nResponse sample:")
                print(json.dumps(response, indent=2)[:1000])
            else:
                print(f"Response: {str(response)[:500]}")
        else:
            print("❌ No response from API")
    
    # Test 2: Get historical chain
    print("\n" + "-"*60)
    print("Test 2: Get historical options chain (2024-12-01)")
    print("-"*60)
    
    historical = feed.get_options_chain('AAPL', date='2024-12-01')
    print(f"Contracts returned: {len(historical)}")
    
    if not historical:
        print("⚠️  No historical contracts - this might be normal if API doesn't support historical snapshots")
    
    # Test 3: Check expiration dates
    print("\n" + "-"*60)
    print("Test 3: Get expiration dates")
    print("-"*60)
    
    expirations = feed.get_expiration_dates('AAPL')
    print(f"Expiration dates: {expirations[:5] if expirations else 'None'}...")
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
    
    return 0

if __name__ == '__main__':
    sys.exit(test_api())

