#!/usr/bin/env python3
"""
Test Live Market Functionality
Validates that the system is working with real market data today
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from alpaca_client import AlpacaClient
from services.massive_price_feed import MassivePriceFeed
from core.live.integrated_trader import IntegratedTrader
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_live_market():
    """Test live market functionality"""
    
    print("="*80)
    print("LIVE MARKET FUNCTIONALITY TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Check market status
    print("1. MARKET STATUS:")
    print("-" * 80)
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        clock = client.api.get_clock()
        is_open = clock.is_open
        print(f"Market: {'✅ OPEN' if is_open else '❌ CLOSED'}")
        if not is_open:
            print(f"Next Open: {clock.next_open}")
        print()
    except Exception as e:
        print(f"❌ Error checking market: {e}")
        return False
    
    # 2. Check Massive availability
    print("2. DATA SOURCE:")
    print("-" * 80)
    massive_feed = MassivePriceFeed()
    if massive_feed.is_available():
        print("✅ Massive Price Feed: Available")
        print(f"   API Key: {'✅ Configured' if massive_feed.api_key else '❌ Missing'}")
    else:
        print("❌ Massive Price Feed: Not Available")
        print("   Will use Alpaca as fallback")
    print()
    
    # 3. Test data fetch
    print("3. DATA FETCH TEST:")
    print("-" * 80)
    test_symbols = ['TSLA', 'PLTR', 'NVDA']
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    for symbol in test_symbols:
        try:
            bars = massive_feed.get_daily_bars(symbol, start_date, end_date, use_1min_aggregation=True)
            if not bars.empty:
                latest_price = bars['close'].iloc[-1]
                print(f"✅ {symbol}: {len(bars)} bars, Latest: ${latest_price:.2f}")
            else:
                print(f"❌ {symbol}: No data")
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")
    print()
    
    # 4. Test integrated trader
    print("4. INTEGRATED TRADER:")
    print("-" * 80)
    try:
        trader = IntegratedTrader(dry_run=True, paper_trading=True)
        
        if trader.massive_price_feed and trader.massive_price_feed.is_available():
            print("✅ Initialized with Massive price feed")
        else:
            print("⚠️  Massive not available, using Alpaca")
        
        # Check risk status
        risk_status = trader.risk_manager.get_risk_status()
        print(f"✅ Risk Status: {risk_status['risk_level']}")
        print(f"   Daily P&L: ${risk_status['daily_pnl']:,.2f}")
        print()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. Test signal generation (if market open)
    if is_open:
        print("5. SIGNAL GENERATION TEST:")
        print("-" * 80)
        
        signals_found = 0
        for symbol in test_symbols[:2]:  # Test first 2
            try:
                bars = None
                if trader.massive_price_feed and trader.massive_price_feed.is_available():
                    bars = trader.massive_price_feed.get_daily_bars(symbol, start_date, end_date, use_1min_aggregation=True)
                else:
                    from alpaca_trade_api.rest import TimeFrame
                    bars = trader.client.get_historical_bars(symbol, TimeFrame.Day, start_date, end_date)
                
                if bars.empty or len(bars) < 30:
                    print(f"{symbol}: ⚠️  Insufficient data ({len(bars)} bars)")
                    continue
                
                intent = trader.orchestrator.analyze_symbol(symbol, bars)
                
                if intent and intent.direction.value != 'FLAT':
                    signals_found += 1
                    print(f"✅ {symbol}: {intent.direction.value} @ {intent.confidence:.2%} ({intent.agent_name})")
                else:
                    print(f"⚠️  {symbol}: No signal")
            except Exception as e:
                print(f"❌ {symbol}: Error - {e}")
        
        print()
        print(f"Signals Generated: {signals_found}/{len(test_symbols[:2])}")
        print()
    else:
        print("5. SIGNAL GENERATION:")
        print("-" * 80)
        print("⚠️  Market closed - signal generation will work when market opens")
        print()
    
    # 6. Summary
    print("="*80)
    print("SYSTEM STATUS SUMMARY")
    print("="*80)
    print(f"Market: {'✅ OPEN' if is_open else '❌ CLOSED'}")
    print(f"Massive Feed: {'✅ Available' if massive_feed.is_available() else '❌ Not Available'}")
    print(f"Integrated Trader: ✅ Initialized")
    print(f"Risk Manager: ✅ Operational")
    print()
    
    if is_open and massive_feed.is_available():
        print("✅ SYSTEM IS READY FOR LIVE TRADING")
        print()
        print("Next steps:")
        print("1. Restart trading system: pkill -f run_daily.py && python run_daily.py --paper")
        print("2. Monitor logs: tail -f logs/tradenova_daily.log")
        print("3. Check dashboard: https://tradenova.fly.dev")
    elif not is_open:
        print("⚠️  Market is closed - system will work when market opens")
    elif not massive_feed.is_available():
        print("⚠️  Massive API not available - check API key")
        print("   System will use Alpaca as fallback")
    
    return True

if __name__ == "__main__":
    success = test_live_market()
    sys.exit(0 if success else 1)

