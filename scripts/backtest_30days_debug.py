#!/usr/bin/env python3
"""
30-Day Backtest with Debugging
Shows why trades aren't being picked
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
import pandas as pd

from config import Config
from alpaca_client import AlpacaClient
from alpaca_trade_api.rest import TimeFrame
from core.multi_agent_orchestrator import MultiAgentOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run 30-day backtest with debugging"""
    print("\n" + "="*70)
    print("30-DAY BACKTEST - DEBUG MODE")
    print("="*70)
    
    # Calculate date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Initialize
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    orchestrator = MultiAgentOrchestrator(client)
    
    # Test a few tickers
    test_tickers = ['NVDA', 'AAPL', 'TSLA', 'META']
    
    print(f"\n📅 Date Range: {start_date.date()} to {end_date.date()}")
    print(f"📊 Testing Tickers: {', '.join(test_tickers)}")
    print("\n" + "="*70)
    print("Analyzing signals...")
    print("="*70 + "\n")
    
    signals_found = 0
    signals_by_ticker = {}
    
    for ticker in test_tickers:
        print(f"\n🔍 Analyzing {ticker}...")
        
        try:
            # Get historical data
            bars = client.get_historical_bars(
                ticker,
                TimeFrame.Day,
                start_date,
                end_date
            )
            
            if bars.empty:
                print(f"  ❌ No data for {ticker}")
                continue
            
            print(f"  ✅ Data: {len(bars)} bars")
            
            # Check if enough data
            if len(bars) < 50:
                print(f"  ⚠️  Insufficient data: {len(bars)} bars (need 50+)")
                print(f"     Trying with available data anyway...")
            
            # Analyze
            trade_intent = orchestrator.analyze_symbol(ticker, bars)
            
            if trade_intent:
                signals_found += 1
                signals_by_ticker[ticker] = {
                    'direction': trade_intent.direction.value,
                    'confidence': trade_intent.confidence,
                    'agent': trade_intent.agent_name,
                    'reasoning': trade_intent.reasoning
                }
                print(f"  ✅ SIGNAL FOUND:")
                print(f"     Direction: {trade_intent.direction.value}")
                print(f"     Confidence: {trade_intent.confidence:.2f}")
                print(f"     Agent: {trade_intent.agent_name}")
                print(f"     Reasoning: {trade_intent.reasoning[:100]}...")
                
                if trade_intent.confidence >= 0.30:
                    print(f"     ✅ Would execute (confidence >= 0.30)")
                else:
                    print(f"     ❌ Would NOT execute (confidence < 0.30)")
            else:
                print(f"  ❌ No signal generated")
                signals_by_ticker[ticker] = None
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            signals_by_ticker[ticker] = None
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Signals Found: {signals_found}/{len(test_tickers)}")
    
    if signals_found > 0:
        print(f"\n✅ Signals generated:")
        for ticker, signal in signals_by_ticker.items():
            if signal:
                print(f"  {ticker}: {signal['direction']} @ {signal['confidence']:.2f} confidence ({signal['agent']})")
    else:
        print(f"\n⚠️  No signals generated. Possible reasons:")
        print(f"  - Insufficient historical data (< 50 bars)")
        print(f"  - Low regime confidence (< 0.4)")
        print(f"  - Agent confidence too low (< 0.30)")
        print(f"  - Market conditions don't meet criteria")
    
    print("="*70)


if __name__ == "__main__":
    main()

