#!/usr/bin/env python3
"""
30-Day Backtest (Fixed)
Extends data range to get enough historical bars for analysis
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta

from config import Config
from backtest_trading import BacktestEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def main():
    """Run 30-day backtest with extended data range"""
    print("\n" + "="*70)
    print("30-DAY BACKTEST - TradeNova (Fixed)")
    print("="*70)
    
    # Calculate date range
    # Backtest period: last 30 days
    end_date = datetime.now()
    backtest_start = end_date - timedelta(days=30)
    
    # Data range: Need 90 days of data to get 50+ bars for analysis
    # (accounting for weekends/holidays, we need ~90 calendar days for 50 trading days)
    data_start = backtest_start - timedelta(days=60)  # Get 60 more days for lookback
    
    # Use all tickers from config
    tickers = Config.TICKERS
    
    print(f"\n📅 Backtest Period: {backtest_start.date()} to {end_date.date()}")
    print(f"📊 Data Range: {data_start.date()} to {end_date.date()} (extended for analysis)")
    print(f"📈 Tickers: {', '.join(tickers)}")
    print(f"💰 Initial Balance: $100,000")
    print("\n" + "="*70)
    print("Starting backtest...")
    print("="*70 + "\n")
    
    # Create backtest engine with extended data range
    # But only trade during the last 30 days
    engine = BacktestEngine(
        tickers=tickers,
        start_date=data_start,  # Extended data range
        end_date=end_date,
        initial_balance=100000.0
    )
    
    # Modify the backtest to only execute trades in the last 30 days
    # We'll do this by modifying the run_backtest method behavior
    # For now, let's just run it and see if we get trades
    
    try:
        engine.run_backtest()
        
        # Filter trades to only those in the backtest period
        backtest_trades = []
        for t in engine.trades:
            entry_time = pd.to_datetime(t['entry_time'])
            # Make timezone-aware if needed
            if entry_time.tzinfo is None:
                entry_time = entry_time.tz_localize('UTC')
            if backtest_start.tzinfo is None:
                backtest_start_aware = backtest_start.replace(tzinfo=entry_time.tzinfo)
            else:
                backtest_start_aware = backtest_start
            if entry_time >= backtest_start_aware:
                backtest_trades.append(t)
        
        # Print summary
        print("\n" + "="*70)
        print("BACKTEST SUMMARY (Last 30 Days)")
        print("="*70)
        print(f"Total Trades in Period: {len(backtest_trades)}")
        print(f"Total Trades (All Data): {len(engine.trades)}")
        
        if len(backtest_trades) > 0:
            print(f"\n✅ Trades were picked in the last 30 days!")
            print(f"\nTrades:")
            for i, trade in enumerate(backtest_trades[:10], 1):
                entry_date = pd.to_datetime(trade['entry_time']).date()
                exit_date = pd.to_datetime(trade['exit_time']).date() if trade.get('exit_time') else 'Open'
                print(f"  {i}. {trade['symbol']} | Entry: {entry_date} @ ${trade['entry_price']:.2f} | "
                      f"Exit: {exit_date} @ ${trade.get('exit_price', 0):.2f} | "
                      f"P&L: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%) | "
                      f"Agent: {trade.get('agent', 'Unknown')}")
        else:
            print(f"\n⚠️  No trades were picked in the last 30 days.")
            if len(engine.trades) > 0:
                print(f"   (But {len(engine.trades)} trades were found in the extended data range)")
            print(f"\nPossible reasons:")
            print(f"  - Signal confidence thresholds too high (need >= 0.30)")
            print(f"  - Regime confidence too low (need >= 0.40)")
            print(f"  - Market conditions didn't meet criteria")
            print(f"  - Risk limits prevented trades")
        
        print("="*70)
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        print(f"\n❌ Backtest failed: {e}")


if __name__ == "__main__":
    import pandas as pd
    main()

