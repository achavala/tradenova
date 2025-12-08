#!/usr/bin/env python3
"""
Test Option Selector
Validates option selection for various tickers and edge cases
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alpaca_client import AlpacaClient
from config import Config
from core.options.option_selector import OptionSelector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_option_selector(ticker: str, side: str = 'buy'):
    """Test option selector for a given ticker"""
    print("="*80)
    print(f"🧪 Testing Option Selector: {ticker} ({side.upper()})")
    print("="*80)
    
    try:
        # Initialize
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        selector = OptionSelector(client)
        
        # Get current price
        current_price = client.get_latest_price(ticker)
        if not current_price:
            print(f"❌ Could not get current price for {ticker}")
            return False
        
        print(f"📊 Current price: ${current_price:.2f}")
        print()
        
        # Test option selection
        import time
        start_time = time.time()
        
        option = selector.pick_best_option(
            ticker=ticker,
            side=side,
            current_price=current_price,
            max_dte=7,
            min_price=0.20,
            max_price=10.00,
            max_spread_pct=15.0
        )
        
        elapsed = time.time() - start_time
        
        if option:
            print()
            print("✅ OPTION SELECTED:")
            print(f"   Symbol: {option['symbol']}")
            print(f"   Strike: ${option['strike']:.2f}")
            print(f"   Expiry: {option['expiry']}")
            print(f"   DTE: {option['dte']} days")
            print(f"   Type: {option['type'].upper()}")
            print(f"   Price: ${option['price']:.2f}")
            print(f"   Bid: ${option['bid']:.2f} | Ask: ${option['ask']:.2f}")
            print(f"   Spread: {option['spread_pct']:.1f}%")
            print(f"   Volume: {option['volume']:,}")
            print(f"   Open Interest: {option['open_interest']:,}")
            print(f"   Strike Distance: {option['strike_distance']*100:.1f}% from ATM")
            print()
            print(f"⏱️  Selection time: {elapsed:.2f} seconds")
            print()
            return True
        else:
            print()
            print("❌ NO OPTION SELECTED")
            print(f"⏱️  Selection time: {elapsed:.2f} seconds")
            print()
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance(tickers: list):
    """Test performance with multiple tickers"""
    print("="*80)
    print("🚀 PERFORMANCE TEST: Multiple Tickers")
    print("="*80)
    print()
    
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    selector = OptionSelector(client)
    
    results = []
    total_start = time.time()
    
    for ticker in tickers:
        try:
            current_price = client.get_latest_price(ticker)
            if not current_price:
                continue
            
            start = time.time()
            option = selector.pick_best_option(
                ticker=ticker,
                side='buy',
                current_price=current_price,
                max_dte=7,
                min_price=0.20,
                max_price=10.00,
                max_spread_pct=15.0
            )
            elapsed = time.time() - start
            
            results.append({
                'ticker': ticker,
                'success': option is not None,
                'time': elapsed,
                'symbol': option['symbol'] if option else None
            })
            
        except Exception as e:
            logger.error(f"Error testing {ticker}: {e}")
            results.append({
                'ticker': ticker,
                'success': False,
                'time': 0,
                'symbol': None,
                'error': str(e)
            })
    
    total_time = time.time() - total_start
    
    print("📊 RESULTS:")
    print()
    for r in results:
        status = "✅" if r['success'] else "❌"
        symbol = r['symbol'] or "N/A"
        time_str = f"{r['time']:.2f}s"
        print(f"  {status} {r['ticker']:6s} | {symbol:25s} | {time_str:>8s}")
    
    print()
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    print(f"⏱️  Average: {total_time/len(tickers):.2f} seconds per ticker")
    print()

if __name__ == '__main__':
    import time
    
    if len(sys.argv) > 1:
        # Test specific ticker
        ticker = sys.argv[1].upper()
        side = sys.argv[2].lower() if len(sys.argv) > 2 else 'buy'
        test_option_selector(ticker, side)
    else:
        # Test multiple tickers
        test_tickers = ['NVDA', 'AAPL', 'TSLA', 'SPY']  # Include SPY to test large chain
        
        print("Testing individual tickers...")
        print()
        
        for ticker in test_tickers:
            test_option_selector(ticker, 'buy')
            time.sleep(1)  # Rate limit
        
        print()
        print("="*80)
        print("Running performance test...")
        print()
        test_performance(['NVDA', 'AAPL', 'TSLA'])

