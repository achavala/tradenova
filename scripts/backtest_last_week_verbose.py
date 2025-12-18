#!/usr/bin/env python3
"""
Last Week Backtest - VERBOSE Version
Shows detailed logging of why trades are/aren't executed
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict

from config import Config
from backtest_trading import BacktestEngine

# Setup verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Also set other loggers to DEBUG
logging.getLogger('core.multi_agent_orchestrator').setLevel(logging.DEBUG)
logging.getLogger('core.regime.classifier').setLevel(logging.DEBUG)


def main():
    """Run verbose backtest"""
    print("\n" + "="*70)
    print("LAST WEEK BACKTEST - VERBOSE MODE")
    print("="*70)
    
    end_date = datetime.now()
    trading_start = end_date - timedelta(days=7)
    data_start = trading_start - timedelta(days=90)
    
    tickers = Config.TICKERS
    
    print(f"\n📅 Trading Window: {trading_start.date()} to {end_date.date()}")
    print(f"📈 Tickers: {len(tickers)} symbols")
    print("="*70)
    print("Running with DEBUG logging...")
    print("="*70 + "\n")
    
    engine = BacktestEngine(
        tickers=tickers,
        start_date=data_start,
        end_date=end_date,
        initial_balance=100000.0
    )
    
    try:
        engine.run_backtest()
        
        # Filter to last week
        trading_window_trades = []
        for t in engine.trades:
            entry_time = pd.to_datetime(t['entry_time'])
            if entry_time.tzinfo is None:
                entry_time = entry_time.tz_localize('UTC')
            if trading_start.tzinfo is None:
                trading_start_aware = trading_start.replace(tzinfo=entry_time.tzinfo)
            else:
                trading_start_aware = trading_start
            if entry_time >= trading_start_aware:
                trading_window_trades.append(t)
        
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"Total Trades (Last 7 Days): {len(trading_window_trades)}")
        print(f"Total Trades (All Period): {len(engine.trades)}")
        print("="*70)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    main()


