#!/usr/bin/env python3
"""
Validate options data for all configured tickers
Shows one contract per ticker in exact JSON format
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
from datetime import datetime
from services.polygon_options_feed import MassiveOptionsFeed
from config import Config

logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)

def validate_all_tickers():
    """Get one option contract per ticker and display in JSON format"""
    
    feed = MassiveOptionsFeed()
    
    if not feed.is_available():
        print("❌ Massive API key not configured")
        return False
    
    print("="*80)
    print("VALIDATING OPTIONS DATA FOR ALL TICKERS")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    tickers = Config.TICKERS
    
    results = {}
    
    for symbol in tickers:
        print(f"Fetching {symbol}...", end=" ", flush=True)
        
        try:
            # Get current price
            current_price = feed._get_current_stock_price(symbol)
            
            if not current_price:
                print("❌ Could not get current price")
                continue
            
            # Get expiration dates
            expirations = feed.get_expiration_dates(symbol)
            
            if not expirations:
                print("❌ No expirations found")
                continue
            
            # Filter to 0-30 DTE range
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
            
            if not valid_expirations:
                print("❌ No valid expirations in 0-30 DTE range")
                continue
            
            # Use first valid expiration
            expiration_date = valid_expirations[0][0]
            
            # Get ATM call option
            contract = feed.get_atm_options(
                symbol,
                expiration_date,
                'call',
                current_price=current_price
            )
            
            if not contract:
                print("❌ No ATM option found")
                continue
            
            # Format contract in exact same structure
            formatted_contract = {
                "details": {
                    "ticker": contract.get('details', {}).get('ticker', 'N/A'),
                    "strike_price": contract.get('details', {}).get('strike_price', 0),
                    "expiration_date": contract.get('details', {}).get('expiration_date', 'N/A'),
                    "contract_type": contract.get('details', {}).get('contract_type', 'N/A'),
                    "shares_per_contract": contract.get('details', {}).get('shares_per_contract', 100)
                },
                "day": {
                    "close": contract.get('day', {}).get('close', 0),
                    "open": contract.get('day', {}).get('open', 0),
                    "high": contract.get('day', {}).get('high', 0),
                    "low": contract.get('day', {}).get('low', 0),
                    "volume": contract.get('day', {}).get('volume', 0),
                    "vwap": contract.get('day', {}).get('vwap', 0)
                },
                "greeks": contract.get('greeks', {}),
                "implied_volatility": contract.get('implied_volatility', 0),
                "open_interest": contract.get('open_interest', 0),
                "break_even_price": contract.get('break_even_price', 0),
                "underlying_asset": contract.get('underlying_asset', {})
            }
            
            results[symbol] = formatted_contract
            print("✅")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.debug(f"Error for {symbol}: {e}", exc_info=True)
            continue
    
    print("\n" + "="*80)
    print("RESULTS - ONE CONTRACT PER TICKER")
    print("="*80)
    print()
    
    for symbol, contract in results.items():
        print(f"// {symbol} - {contract['details']['ticker']}")
        print(f"// Strike: ${contract['details']['strike_price']}, Expiration: {contract['details']['expiration_date']}")
        print(f"// Current Price: ${contract['underlying_asset'].get('price', 'N/A')}")
        print(f"// Last Price: ${contract['day']['close']}, Volume: {contract['day']['volume']:,}")
        print(f"// IV: {contract['implied_volatility']:.2%}, OI: {contract['open_interest']:,}")
        print()
        print(json.dumps(contract, indent=2))
        print()
        print("-" * 80)
        print()
    
    print(f"\n✅ Successfully retrieved contracts for {len(results)}/{len(tickers)} tickers")
    
    return len(results) == len(tickers)

if __name__ == "__main__":
    success = validate_all_tickers()
    sys.exit(0 if success else 1)




