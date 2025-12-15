#!/usr/bin/env python3
"""
Quick 30-Day Backtest
Run backtest for the last 30 days to see if trades are being picked
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
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Run 30-day backtest"""
    print("\n" + "="*70)
    print("30-DAY BACKTEST - TradeNova")
    print("="*70)
    
    # Calculate date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Use all tickers from config
    tickers = Config.TICKERS
    
    print(f"\n📅 Date Range: {start_date.date()} to {end_date.date()}")
    print(f"📊 Tickers: {', '.join(tickers)}")
    print(f"💰 Initial Balance: $100,000")
    print("\n" + "="*70)
    print("Starting backtest...")
    print("="*70 + "\n")
    
    # Create backtest engine
    engine = BacktestEngine(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        initial_balance=100000.0
    )
    
    # Run backtest
    try:
        engine.run_backtest()
        
        # Print summary
        print("\n" + "="*70)
        print("BACKTEST SUMMARY")
        print("="*70)
        print(f"Total Trades: {len(engine.trades)}")
        
        if len(engine.trades) > 0:
            print(f"\n✅ Trades were picked! See details above.")
            print(f"\nFirst few trades:")
            for i, trade in enumerate(engine.trades[:5], 1):
                print(f"  {i}. {trade['symbol']} | Entry: ${trade['entry_price']:.2f} | "
                      f"Exit: ${trade['exit_price']:.2f} | P&L: ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
        else:
            print(f"\n⚠️  No trades were picked in the last 30 days.")
            print(f"This could mean:")
            print(f"  - Signal confidence thresholds are too high")
            print(f"  - Market conditions didn't meet criteria")
            print(f"  - Risk limits prevented trades")
        
        print("="*70)
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        print(f"\n❌ Backtest failed: {e}")


if __name__ == "__main__":
    main()

