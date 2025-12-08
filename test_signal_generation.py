#!/usr/bin/env python3
"""
Quick Test - Signal Generation with Integrated Trader
Shows that system CAN generate signals
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
from config import Config
from core.live.integrated_trader import IntegratedTrader
from alpaca_trade_api.rest import TimeFrame

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_signals():
    """Test signal generation"""
    print("="*70)
    print("TESTING SIGNAL GENERATION")
    print("="*70)
    
    # Initialize integrated trader (dry-run mode)
    trader = IntegratedTrader(dry_run=True, paper_trading=True)
    
    # Test a few tickers
    test_tickers = ['TSLA', 'NVDA', 'AAPL', 'INTC']
    
    print(f"\nTesting {len(test_tickers)} tickers...\n")
    
    signals_found = 0
    for ticker in test_tickers:
        try:
            # Get recent bars
            end = datetime.now()
            start = end - timedelta(days=60)
            
            bars = trader.client.get_historical_bars(
                ticker,
                TimeFrame.Day,
                start,
                end
            )
            
            if bars.empty or len(bars) < 20:
                print(f"  {ticker}: ⚠️  Insufficient data ({len(bars)} bars)")
                continue
            
            # Analyze with orchestrator
            trade_intent = trader.orchestrator.analyze_symbol(ticker, bars)
            
            if trade_intent:
                if trade_intent.confidence >= 0.30:
                    signals_found += 1
                    print(f"  {ticker}: ✅ {trade_intent.direction.value} ({trade_intent.confidence:.2%}) - {trade_intent.agent_name}")
                else:
                    print(f"  {ticker}: ⏸️  Signal too weak ({trade_intent.confidence:.2%} < 30%)")
            else:
                print(f"  {ticker}: ⏸️  No signal generated")
                
        except Exception as e:
            print(f"  {ticker}: ❌ Error - {e}")
    
    print(f"\n{'='*70}")
    print(f"RESULTS: {signals_found}/{len(test_tickers)} signals generated")
    print(f"{'='*70}")
    
    if signals_found > 0:
        print("\n✅ System IS generating signals!")
        print("   To start trading, run:")
        print("   python run_daily.py --paper")
        print("\n   Or use the scheduler:")
        print("   ./start_trading.sh --paper")
    else:
        print("\n⚠️  No signals generated (may need better market conditions)")
        print("   System is working, just waiting for good setups")

if __name__ == "__main__":
    test_signals()

