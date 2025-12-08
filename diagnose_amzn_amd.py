#!/usr/bin/env python3
"""
Diagnose AMZN and AMD Data Access Issues
Test different approaches to get data for these tickers
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
from config import Config
from alpaca_client import AlpacaClient
from alpaca_trade_api.rest import TimeFrame, REST

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ticker_data_access(ticker, client):
    """Test different methods to get data for a ticker"""
    print(f"\n{'='*70}")
    print(f"TESTING: {ticker}")
    print(f"{'='*70}")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Test 1: Standard get_historical_bars
    print(f"\n1. Testing standard get_historical_bars()...")
    try:
        bars = client.get_historical_bars(
            ticker,
            TimeFrame.Day,
            start_date,
            end_date
        )
        if not bars.empty:
            print(f"   ✅ SUCCESS: Got {len(bars)} bars")
            print(f"   Date range: {bars.index[0]} to {bars.index[-1]}")
            return True, bars
        else:
            print(f"   ❌ FAILED: Empty DataFrame returned")
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ FAILED: {error_msg[:100]}")
        
        # Check if it's a subscription issue
        if "subscription" in error_msg.lower() or "sip" in error_msg.lower():
            print(f"   ⚠️  Subscription/data feed limitation detected")
    
    # Test 2: Try with different timeframes
    print(f"\n2. Testing different timeframes...")
    for tf in [TimeFrame.Week, TimeFrame.Hour]:
        try:
            bars = client.get_historical_bars(
                ticker,
                tf,
                start_date,
                end_date
            )
            if not bars.empty:
                print(f"   ✅ SUCCESS with {tf}: Got {len(bars)} bars")
                return True, bars
        except Exception as e:
            print(f"   ❌ {tf}: {str(e)[:60]}")
    
    # Test 3: Try direct API call
    print(f"\n3. Testing direct Alpaca API call...")
    try:
        api = client.api
        bars = api.get_bars(
            ticker,
            TimeFrame.Day,
            start_date.isoformat(),
            end_date.isoformat(),
            adjustment='raw'
        )
        if bars:
            print(f"   ✅ SUCCESS: Got {len(bars)} bars via direct API")
            return True, bars
    except Exception as e:
        print(f"   ❌ Direct API failed: {str(e)[:100]}")
    
    # Test 4: Try with different date ranges
    print(f"\n4. Testing different date ranges...")
    test_ranges = [
        (30, "30 days"),
        (60, "60 days"),
        (120, "120 days"),
    ]
    
    for days, label in test_ranges:
        try:
            test_start = end_date - timedelta(days=days)
            bars = client.get_historical_bars(
                ticker,
                TimeFrame.Day,
                test_start,
                end_date
            )
            if not bars.empty:
                print(f"   ✅ SUCCESS with {label}: Got {len(bars)} bars")
                return True, bars
        except Exception as e:
            print(f"   ❌ {label}: {str(e)[:60]}")
    
    # Test 5: Check if ticker symbol is correct
    print(f"\n5. Verifying ticker symbol...")
    try:
        # Try to get latest quote
        latest = client.get_latest_price(ticker)
        if latest:
            print(f"   ✅ Ticker is valid: Latest price = ${latest:.2f}")
        else:
            print(f"   ⚠️  Could not get latest price")
    except Exception as e:
        print(f"   ❌ Error getting latest price: {str(e)[:60]}")
    
    # Test 6: Check account data permissions
    print(f"\n6. Checking account data permissions...")
    try:
        account = client.get_account()
        print(f"   Account Number: {account.get('account_number', 'N/A')}")
        print(f"   Pattern Day Trader: {account.get('pattern_day_trader', False)}")
        print(f"   Trading Blocked: {account.get('trading_blocked', False)}")
        
        # Try to get a working ticker for comparison
        print(f"\n   Comparing with working ticker (AAPL)...")
        try:
            aapl_bars = client.get_historical_bars(
                'AAPL',
                TimeFrame.Day,
                start_date,
                end_date
            )
            if not aapl_bars.empty:
                print(f"   ✅ AAPL works: {len(aapl_bars)} bars")
                print(f"   ⚠️  This confirms subscription works, but {ticker} has specific issue")
        except Exception as e:
            print(f"   ❌ Even AAPL failed: {str(e)[:60]}")
            
    except Exception as e:
        print(f"   ❌ Error checking account: {str(e)[:60]}")
    
    return False, None

def main():
    """Main diagnostic function"""
    print("="*70)
    print("DIAGNOSING AMZN AND AMD DATA ACCESS ISSUES")
    print("="*70)
    
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    # Test both tickers
    results = {}
    
    for ticker in ['AMZN', 'AMD']:
        success, bars = test_ticker_data_access(ticker, client)
        results[ticker] = {
            'success': success,
            'bars_count': len(bars) if bars is not None else 0
        }
    
    # Summary
    print("\n" + "="*70)
    print("DIAGNOSIS SUMMARY")
    print("="*70)
    
    for ticker, result in results.items():
        status = "✅ WORKING" if result['success'] else "❌ NOT WORKING"
        print(f"\n{ticker}: {status}")
        if result['success']:
            print(f"   Bars retrieved: {result['bars_count']}")
        else:
            print(f"   Issue: Could not retrieve historical data")
            print(f"   Possible causes:")
            print(f"     1. Ticker requires premium data subscription")
            print(f"     2. Ticker symbol format issue")
            print(f"     3. Data feed limitation for this specific ticker")
            print(f"     4. Subscription upgrade not fully propagated")
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    if not results['AMZN']['success'] or not results['AMD']['success']:
        print("\n1. Check Alpaca Dashboard:")
        print("   - Verify subscription level")
        print("   - Check if AMZN/AMD require premium data")
        print("   - Look for any ticker-specific restrictions")
        
        print("\n2. Try Alternative Approaches:")
        print("   - Use yfinance for historical data (free)")
        print("   - Use Alpha Vantage API (free tier)")
        print("   - Contact Alpaca support about these specific tickers")
        
        print("\n3. Temporary Workaround:")
        print("   - Remove AMZN and AMD from Config.TICKERS")
        print("   - System will work with 10/12 tickers (83% coverage)")
        print("   - Add them back when data access is resolved")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()

