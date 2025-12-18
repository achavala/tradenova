#!/usr/bin/env python3
"""
Get REAL options data from Massive - with prices, Greeks, premiums
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import json
import requests
from datetime import datetime
from config import Config

def get_real_options_data():
    """Get real options data with prices and Greeks"""
    
    api_key = Config.MASSIVE_API_KEY or os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ API key not configured")
        return
    
    symbol = "NVDA"
    print(f"Getting REAL options data for {symbol}")
    print("="*80)
    
    # Use the snapshot endpoint which has REAL prices and Greeks
    url = f"https://api.polygon.io/v3/snapshot/options/{symbol}"
    params = {
        'apiKey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'OK' and 'results' in data:
                results = data['results']
                print(f"✅ Retrieved {len(results)} option contracts with REAL data\n")
                
                # Filter to calls with reasonable strikes (near ATM)
                # Get current stock price from first result
                current_price = None
                if results:
                    underlying = results[0].get('underlying_asset', {})
                    current_price = underlying.get('price')
                    if current_price:
                        print(f"📊 Current {symbol} Price: ${current_price:.2f}\n")
                
                # Filter calls near ATM
                calls_near_atm = []
                for opt in results:
                    details = opt.get('details', {})
                    if details.get('contract_type') == 'call':
                        strike = details.get('strike_price', 0)
                        if current_price and 0.5 <= strike / current_price <= 1.5:  # Within 50% of current price
                            calls_near_atm.append(opt)
                
                # Sort by strike
                calls_near_atm.sort(key=lambda x: x.get('details', {}).get('strike_price', 0))
                
                print(f"📈 CALLS NEAR ATM (strike within 50% of ${current_price:.2f}):\n")
                print("-" * 120)
                
                for i, opt in enumerate(calls_near_atm[:10]):  # Show first 10
                    details = opt.get('details', {})
                    day = opt.get('day', {})
                    greeks = opt.get('greeks', {})
                    
                    strike = details.get('strike_price', 0)
                    expiration = details.get('expiration_date', 'N/A')
                    ticker = details.get('ticker', 'N/A')
                    
                    # Price data
                    last_price = day.get('close', day.get('last_updated', 0))
                    bid = day.get('open', 0)  # Using open as proxy - need to check actual fields
                    ask = day.get('high', 0)
                    volume = day.get('volume', 0)
                    open_interest = opt.get('open_interest', 0)
                    
                    # Greeks
                    delta = greeks.get('delta', 'N/A')
                    gamma = greeks.get('gamma', 'N/A')
                    theta = greeks.get('theta', 'N/A')
                    vega = greeks.get('vega', 'N/A')
                    iv = greeks.get('implied_volatility', 'N/A')
                    
                    print(f"\nContract {i+1}:")
                    print(f"  Ticker: {ticker}")
                    print(f"  Strike: ${strike:.2f}")
                    print(f"  Expiration: {expiration}")
                    print(f"  Last Price: ${last_price:.2f}" if isinstance(last_price, (int, float)) else f"  Last Price: {last_price}")
                    print(f"  Volume: {volume}")
                    print(f"  Open Interest: {open_interest}")
                    
                    if greeks:
                        print(f"  Greeks:")
                        print(f"    Delta: {delta}")
                        print(f"    Gamma: {gamma}")
                        print(f"    Theta: {theta}")
                        print(f"    Vega: {vega}")
                        print(f"    IV: {iv}")
                    else:
                        print(f"  ⚠️  Greeks: Not available (may need higher subscription tier)")
                
                # Show full structure of first contract
                print("\n" + "="*80)
                print("FULL CONTRACT STRUCTURE (First Result):")
                print("="*80)
                print(json.dumps(results[0], indent=2))
                
            else:
                print(f"❌ Unexpected response format:")
                print(json.dumps(data, indent=2))
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_real_options_data()

