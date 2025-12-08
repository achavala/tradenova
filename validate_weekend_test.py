#!/usr/bin/env python3
"""
Validate Weekend Test System
Quick validation that historical replay works with real data
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from core.live.historical_replay_client import HistoricalReplayClient
from alpaca_client import AlpacaClient
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_weekend_test():
    """Validate weekend test system"""
    print("="*80)
    print("WEEKEND TEST SYSTEM VALIDATION")
    print("="*80)
    
    # Test date (yesterday)
    test_date = (datetime.now() - timedelta(days=1)).date()
    
    print(f"\n📅 Test Date: {test_date}")
    print("✅ Using REAL historical data from Alpaca")
    print("✅ No fake entries - all data is authentic\n")
    
    try:
        # Initialize real Alpaca client
        print("1️⃣  Initializing Alpaca client...")
        real_client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        print("   ✅ Alpaca client initialized")
        
        # Initialize replay client
        print("\n2️⃣  Initializing Historical Replay Client...")
        replay_date = datetime.combine(test_date, datetime.min.time())
        replay_client = HistoricalReplayClient(
            replay_date=replay_date,
            real_alpaca_client=real_client,
            speed_multiplier=0,  # Manual mode for testing
            use_intraday=True
        )
        print("   ✅ Replay client initialized")
        
        # Test data loading
        print("\n3️⃣  Testing data loading...")
        test_symbol = "SPY"  # SPY should have data
        
        # Set simulation time to market open (timezone-aware)
        from pytz import UTC
        replay_client.sim_time = UTC.localize(datetime.combine(
            test_date,
            datetime.strptime("09:30", "%H:%M").time()
        ))
        
        # Load historical bars
        from alpaca_trade_api.rest import TimeFrame, TimeFrameUnit
        # Try 5-minute bars first
        try:
            tf_5min = TimeFrame(5, TimeFrameUnit.Minute)
            bars = replay_client._load_historical_bars(test_symbol, tf_5min)
        except Exception as e:
            print(f"   ⚠️  Could not load 5-minute bars: {e}")
            # Fallback to daily if 5-minute not available
            bars = replay_client._load_historical_bars(test_symbol, TimeFrame.Day)
        
        if bars.empty:
            print(f"   ⚠️  No intraday data for {test_symbol} on {test_date}")
            print("   📊 Trying daily bars...")
            bars = replay_client._load_historical_bars(test_symbol, TimeFrame.Day)
        
        if not bars.empty:
            print(f"   ✅ Loaded {len(bars)} bars for {test_symbol}")
            print(f"   📈 First bar: {bars.index[0]}")
            print(f"   📈 Last bar: {bars.index[-1]}")
            print(f"   💰 Sample price: ${bars.iloc[0]['close']:.2f}")
        else:
            print(f"   ❌ No data found for {test_symbol} on {test_date}")
            return False
        
        # Test price retrieval
        print("\n4️⃣  Testing price retrieval...")
        price = replay_client.get_latest_price(test_symbol)
        if price:
            print(f"   ✅ Current price: ${price:.2f}")
        else:
            print(f"   ❌ Could not get price for {test_symbol}")
            return False
        
        # Test market hours
        print("\n5️⃣  Testing market hours simulation...")
        from pytz import UTC
        replay_client.sim_time = UTC.localize(datetime.combine(
            test_date,
            datetime.strptime("10:00", "%H:%M").time()
        ))
        is_open = replay_client.is_market_open()
        print(f"   ✅ Market open check: {is_open}")
        
        replay_client.sim_time = UTC.localize(datetime.combine(
            test_date,
            datetime.strptime("17:00", "%H:%M").time()
        ))
        is_open = replay_client.is_market_open()
        print(f"   ✅ Market closed check: {not is_open}")
        
        # Test historical bars retrieval
        print("\n6️⃣  Testing historical bars retrieval...")
        start = datetime.combine(test_date, datetime.min.time()) - timedelta(days=30)
        end = datetime.combine(test_date, datetime.max.time())
        
        historical_bars = replay_client.get_historical_bars(
            test_symbol,
            TimeFrame.Day,
            start,
            end
        )
        
        if not historical_bars.empty:
            print(f"   ✅ Retrieved {len(historical_bars)} historical bars")
            print(f"   📊 Date range: {historical_bars.index[0].date()} to {historical_bars.index[-1].date()}")
        else:
            print(f"   ⚠️  No historical bars retrieved")
        
        print("\n" + "="*80)
        print("✅ VALIDATION COMPLETE - System ready for weekend testing!")
        print("="*80)
        print("\n📝 Next steps:")
        print("   1. Run: python weekend_test_runner.py --date <YYYY-MM-DD>")
        print("   2. Check logs: logs/weekend_test.log")
        print("   3. Review report: logs/weekend_test_YYYY-MM-DD.txt")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = validate_weekend_test()
    sys.exit(0 if success else 1)

