#!/usr/bin/env python3
"""
Test Option Selector with Live Market Data
Validates selector behavior during market hours with real spreads, IV, and pricing
"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from alpaca_client import AlpacaClient
from config import Config
from core.options.option_selector import OptionSelector

def test_selector_live():
    """Test option selector with live market data"""
    print("="*80)
    print("🧪 Testing Option Selector with Live Market Data")
    print("="*80)
    print()
    
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    selector = OptionSelector(client)
    
    # Test tickers
    test_tickers = Config.TICKERS[:10]  # First 10 tickers
    
    print(f"📊 Testing {len(test_tickers)} tickers:")
    print(f"   {', '.join(test_tickers)}")
    print()
    
    results = []
    
    for ticker in test_tickers:
        try:
            print(f"🔍 Testing {ticker}...")
            
            # Get current price
            current_price = client.get_latest_price(ticker)
            if not current_price:
                print(f"   ⚠️  No price data for {ticker}, skipping")
                continue
            
            print(f"   Current price: ${current_price:.2f}")
            
            # Test CALL selection
            start_time = time.time()
            result = selector.pick_best_option(
                ticker=ticker,
                side='buy',
                current_price=current_price,
                max_dte=7,
                min_price=0.20,
                max_price=None,  # Use dynamic calculation
                max_spread_pct=15.0
            )
            selection_time = time.time() - start_time
            
            if result:
                results.append({
                    'ticker': ticker,
                    'selected': True,
                    'symbol': result['symbol'],
                    'strike': result['strike'],
                    'price': result['price'],
                    'dte': result['dte'],
                    'time': selection_time
                })
                print(f"   ✅ Selected: {result['symbol']}")
                print(f"      Strike: ${result['strike']:.2f} | Price: ${result['price']:.2f} | DTE: {result['dte']}")
                print(f"      Selection time: {selection_time:.2f}s")
            else:
                results.append({
                    'ticker': ticker,
                    'selected': False,
                    'time': selection_time
                })
                print(f"   ❌ No option selected")
                print(f"      Selection time: {selection_time:.2f}s")
            
            print()
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()
            continue
    
    # Summary
    print("="*80)
    print("📊 Test Summary")
    print("="*80)
    print()
    
    selected_count = sum(1 for r in results if r.get('selected', False))
    total_time = sum(r['time'] for r in results)
    avg_time = total_time / len(results) if results else 0
    
    print(f"✅ Selected options: {selected_count}/{len(results)}")
    print(f"⏱️  Average selection time: {avg_time:.2f}s")
    print(f"⏱️  Total time: {total_time:.2f}s")
    print()
    
    if selected_count > 0:
        print("Selected Options:")
        for r in results:
            if r.get('selected'):
                print(f"  {r['ticker']:6s} → {r['symbol']:25s} | Strike: ${r['strike']:6.2f} | Price: ${r['price']:5.2f} | DTE: {r['dte']:2d}")
    
    print()
    print("✅ Live validation complete!")
    print()
    print("Next steps:")
    print("  1. Monitor daemon logs: tail -f logs/tradenova_daemon.log | grep -E 'SELECTED|REASONING'")
    print("  2. Check dashboard for option positions")
    print("  3. Validate fills and execution")

if __name__ == '__main__':
    test_selector_live()

