#!/usr/bin/env python3
"""
7-Day Backtest Debug - Shows why trades aren't being picked
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
    """Debug 7-day backtest"""
    print("\n" + "="*70)
    print("7-DAY BACKTEST DEBUG - Signal Analysis")
    print("="*70)
    
    # Last 7 days
    end_date = datetime.now()
    backtest_start = end_date - timedelta(days=7)
    data_start = backtest_start - timedelta(days=60)
    
    # Initialize
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    orchestrator = MultiAgentOrchestrator(client)
    
    # Test tickers
    test_tickers = Config.TICKERS[:6]
    
    print(f"\n📅 Period: {backtest_start.date()} to {end_date.date()}")
    print(f"📊 Testing: {', '.join(test_tickers)}")
    print("\n" + "="*70)
    print("Analyzing signals for each day...")
    print("="*70 + "\n")
    
    # Get all trading days in the period
    all_bars = {}
    for ticker in test_tickers:
        bars = client.get_historical_bars(
            ticker,
            TimeFrame.Day,
            data_start,
            end_date
        )
        if not bars.empty:
            all_bars[ticker] = bars
    
    # Analyze each day in the last 7 days
    signals_by_day = {}
    total_signals = 0
    signals_above_threshold = 0
    
    # Get unique dates in the last 7 days
    if all_bars:
        all_dates = set()
        for bars in all_bars.values():
            dates = bars.index if isinstance(bars.index, pd.DatetimeIndex) else pd.to_datetime(bars.index)
            # Filter to last 7 days
            for date in dates:
                if pd.to_datetime(date).date() >= backtest_start.date():
                    all_dates.add(pd.to_datetime(date).date())
        
        sorted_dates = sorted(all_dates)
        
        print(f"📅 Trading Days in Last 7 Days: {len(sorted_dates)}")
        print(f"   Dates: {', '.join([d.strftime('%Y-%m-%d') for d in sorted_dates])}\n")
        
        for date in sorted_dates:
            date_str = date.strftime('%Y-%m-%d')
            signals_by_day[date_str] = []
            
            for ticker in test_tickers:
                if ticker not in all_bars:
                    continue
                
                bars = all_bars[ticker]
                # Get bars up to this date (handle timezone)
                date_ts = pd.Timestamp(date).tz_localize('UTC') if bars.index.tz else pd.Timestamp(date)
                bars_up_to_date = bars[bars.index <= date_ts]
                
                if len(bars_up_to_date) < 50:
                    continue
                
                try:
                    trade_intent = orchestrator.analyze_symbol(ticker, bars_up_to_date)
                    
                    if trade_intent:
                        total_signals += 1
                        signal_info = {
                            'ticker': ticker,
                            'direction': trade_intent.direction.value,
                            'confidence': trade_intent.confidence,
                            'agent': trade_intent.agent_name,
                            'above_threshold': trade_intent.confidence >= 0.30
                        }
                        signals_by_day[date_str].append(signal_info)
                        
                        if trade_intent.confidence >= 0.30:
                            signals_above_threshold += 1
                            print(f"✅ {date_str} {ticker:6s}: {trade_intent.direction.value:5s} "
                                  f"@ {trade_intent.confidence:.2f} confidence "
                                  f"({trade_intent.agent_name}) - WOULD TRADE")
                        else:
                            print(f"⚠️  {date_str} {ticker:6s}: {trade_intent.direction.value:5s} "
                                  f"@ {trade_intent.confidence:.2f} confidence "
                                  f"({trade_intent.agent_name}) - BELOW THRESHOLD (0.30)")
                
                except Exception as e:
                    logger.debug(f"Error analyzing {ticker} on {date_str}: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("SIGNAL ANALYSIS SUMMARY")
    print("="*70)
    print(f"Total Signals Generated: {total_signals}")
    print(f"Signals Above Threshold (>=0.30): {signals_above_threshold}")
    print(f"Signals Below Threshold: {total_signals - signals_above_threshold}")
    
    if total_signals == 0:
        print(f"\n⚠️  No signals generated in last 7 days")
        print(f"   Possible reasons:")
        print(f"   - Regime confidence too low (< 0.40)")
        print(f"   - Market conditions don't meet agent criteria")
        print(f"   - Not enough trading days (weekends/holidays)")
    elif signals_above_threshold == 0:
        print(f"\n⚠️  Signals generated but all below confidence threshold (0.30)")
        print(f"   Consider lowering threshold or checking agent confidence logic")
    else:
        print(f"\n✅ {signals_above_threshold} signals above threshold - trades should execute")
    
    print("="*70)


if __name__ == "__main__":
    main()

