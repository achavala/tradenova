#!/usr/bin/env python3
"""
Test what data Alpaca actually returns for options chain
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from alpaca_client import AlpacaClient
from config import Config
from services.options_data_feed import OptionsDataFeed

def test_options_chain_data():
    """Test what fields are actually in the options chain response"""
    print("="*80)
    print("🔍 Testing Alpaca Options Chain Data")
    print("="*80)
    print()
    
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    feed = OptionsDataFeed(client)
    
    # Test NVDA
    symbol = "NVDA"
    print(f"Fetching options chain for {symbol}...")
    print()
    
    chain = feed.get_options_chain(symbol)
    
    if not chain:
        print("❌ No chain data returned")
        return
    
    print(f"✅ Retrieved {len(chain)} contracts")
    print()
    
    # Show first contract structure
    if len(chain) > 0:
        first = chain[0]
        print("📋 First Contract Structure:")
        print("-" * 80)
        
        if isinstance(first, dict):
            print("Type: Dictionary")
            print("\nAll Keys:")
            for key in sorted(first.keys()):
                value = first[key]
                value_str = str(value)[:50] if value is not None else "None"
                print(f"  {key:30s}: {value_str}")
            
            print("\n" + "="*80)
            print("🔍 Checking for Price Fields:")
            print("-" * 80)
            
            price_fields = ['bid', 'ask', 'bid_price', 'ask_price', 'last', 'last_price', 
                          'close', 'settlement_price', 'mid', 'mark', 'theoretical']
            
            for field in price_fields:
                if field in first:
                    print(f"  ✅ {field:20s}: {first[field]}")
                else:
                    # Check variations
                    variations = [f"{field}_price", f"{field}_value", f"option_{field}"]
                    found = False
                    for var in variations:
                        if var in first:
                            print(f"  ✅ {var:20s}: {first[var]}")
                            found = True
                            break
                    if not found:
                        print(f"  ❌ {field:20s}: Not found")
        else:
            print("Type: Object")
            print("\nAll Attributes:")
            for attr in sorted(dir(first)):
                if not attr.startswith('_'):
                    try:
                        value = getattr(first, attr)
                        value_str = str(value)[:50] if value is not None else "None"
                        print(f"  {attr:30s}: {value_str}")
                    except:
                        pass
            
            print("\n" + "="*80)
            print("🔍 Checking for Price Fields:")
            print("-" * 80)
            
            price_fields = ['bid', 'ask', 'bid_price', 'ask_price', 'last', 'last_price', 
                          'close', 'settlement_price', 'mid', 'mark', 'theoretical']
            
            for field in price_fields:
                if hasattr(first, field):
                    value = getattr(first, field, None)
                    print(f"  ✅ {field:20s}: {value}")
                else:
                    print(f"  ❌ {field:20s}: Not found")
        
        print()
        print("="*80)
        print("📊 Sample Contracts (first 3):")
        print("-" * 80)
        
        for i, contract in enumerate(chain[:3], 1):
            if isinstance(contract, dict):
                symbol = contract.get('symbol') or contract.get('contract_symbol', 'N/A')
                strike = contract.get('strike_price') or contract.get('strike', 'N/A')
                expiry = contract.get('expiration_date') or contract.get('exp_date', 'N/A')
                bid = contract.get('bid') or contract.get('bid_price', 'N/A')
                ask = contract.get('ask') or contract.get('ask_price', 'N/A')
                last = contract.get('last') or contract.get('last_price', 'N/A')
            else:
                symbol = getattr(contract, 'symbol', None) or getattr(contract, 'contract_symbol', 'N/A')
                strike = getattr(contract, 'strike_price', None) or getattr(contract, 'strike', 'N/A')
                expiry = getattr(contract, 'expiration_date', None) or getattr(contract, 'exp_date', 'N/A')
                bid = getattr(contract, 'bid', None) or getattr(contract, 'bid_price', None)
                ask = getattr(contract, 'ask', None) or getattr(contract, 'ask_price', None)
                last = getattr(contract, 'last', None) or getattr(contract, 'last_price', None)
            
            print(f"\nContract #{i}:")
            print(f"  Symbol: {symbol}")
            print(f"  Strike: {strike}")
            print(f"  Expiry: {expiry}")
            print(f"  Bid:    {bid}")
            print(f"  Ask:    {ask}")
            print(f"  Last:   {last}")

if __name__ == '__main__':
    test_options_chain_data()

