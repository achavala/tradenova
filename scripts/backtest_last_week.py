#!/usr/bin/env python3
"""
Last Week Backtest - Target: 2-5 trades per day
Uses extended data range (90+ days) for proper analysis
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def main():
    """Run last week backtest with target of 2-5 trades per day"""
    print("\n" + "="*70)
    print("LAST WEEK BACKTEST - Target: 2-5 Trades Per Day")
    print("="*70)
    
    # Calculate date ranges
    end_date = datetime.now()
    trading_start = end_date - timedelta(days=7)  # Last 7 days
    data_start = trading_start - timedelta(days=90)  # 90 days before for analysis
    
    # Use all tickers
    tickers = Config.TICKERS
    
    print(f"\n📅 Analysis Window: {data_start.date()} to {end_date.date()} (90+ days)")
    print(f"📅 Trading Window: {trading_start.date()} to {end_date.date()} (Last 7 days)")
    print(f"📈 Tickers: {', '.join(tickers)}")
    print(f"💰 Initial Balance: $100,000")
    print(f"\n🎯 Target: 2-5 trades per day")
    print("="*70)
    print("Starting backtest...")
    print("="*70 + "\n")
    
    # Create backtest engine
    engine = BacktestEngine(
        tickers=tickers,
        start_date=data_start,  # Extended for proper analysis
        end_date=end_date,
        initial_balance=100000.0
    )
    
    try:
        engine.run_backtest()
        
        # Filter trades to last week only
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
        
        # Analyze by day
        trades_by_day = defaultdict(list)
        for trade in trading_window_trades:
            entry_date = pd.to_datetime(trade['entry_time']).date()
            trades_by_day[entry_date].append(trade)
        
        # Results
        print("\n" + "="*70)
        print("LAST WEEK BACKTEST RESULTS")
        print("="*70)
        
        total_trades = len(trading_window_trades)
        trading_days = len(trades_by_day)
        
        print(f"\n📊 Total Trades (Last 7 Days): {total_trades}")
        print(f"📅 Trading Days with Trades: {trading_days}")
        
        if total_trades > 0:
            print(f"\n📈 Trades Per Day:")
            print(f"{'='*70}")
            for date in sorted(trades_by_day.keys()):
                day_trades = trades_by_day[date]
                print(f"{date}: {len(day_trades)} trades")
                for trade in day_trades:
                    pnl_sign = '+' if trade['pnl'] >= 0 else ''
                    print(f"  - {trade['symbol']:6s} | {pnl_sign}${trade['pnl']:7,.2f} | {trade.get('agent', 'Unknown')}")
            
            # Check if meeting target
            avg_trades_per_day = total_trades / max(trading_days, 1)
            print(f"\n📊 Average Trades Per Day: {avg_trades_per_day:.1f}")
            
            if avg_trades_per_day < 2:
                print(f"\n⚠️  BELOW TARGET: {avg_trades_per_day:.1f} trades/day (target: 2-5)")
                print(f"   Possible reasons:")
                print(f"   - Confidence thresholds too high (current: >= 0.30)")
                print(f"   - Regime confidence too low (current: >= 0.40)")
                print(f"   - Market conditions didn't meet criteria")
                print(f"   - Too many positions already open (max: 10)")
            elif avg_trades_per_day > 5:
                print(f"\n⚠️  ABOVE TARGET: {avg_trades_per_day:.1f} trades/day (target: 2-5)")
                print(f"   Consider:")
                print(f"   - Raising confidence thresholds")
                print(f"   - Tightening regime filters")
            else:
                print(f"\n✅ WITHIN TARGET: {avg_trades_per_day:.1f} trades/day (target: 2-5)")
            
            # Agent analysis
            agent_stats = defaultdict(lambda: {'count': 0, 'pnl': 0.0})
            for trade in trading_window_trades:
                agent = trade.get('agent', 'Unknown')
                agent_stats[agent]['count'] += 1
                agent_stats[agent]['pnl'] += trade['pnl']
            
            print(f"\n🤖 Trades by Agent:")
            print(f"{'='*70}")
            for agent, stats in sorted(agent_stats.items(), key=lambda x: x[1]['count'], reverse=True):
                print(f"{agent:20s}: {stats['count']:3d} trades | P&L: ${stats['pnl']:8,.2f}")
            
        else:
            print(f"\n❌ NO TRADES in last week")
            print(f"\nDiagnosis:")
            print(f"  - Total trades in all period: {len(engine.trades)}")
            if len(engine.trades) > 0:
                print(f"  - Trades found but outside 7-day window")
                print(f"  - System may need lower thresholds for 7-day window")
            else:
                print(f"  - No trades found at all")
                print(f"  - Check confidence thresholds and regime filters")
        
        # Performance
        if total_trades > 0:
            winning = [t for t in trading_window_trades if t['pnl'] > 0]
            total_pnl = sum(t['pnl'] for t in trading_window_trades)
            win_rate = (len(winning) / total_trades * 100) if total_trades > 0 else 0
            
            print(f"\n💰 Performance:")
            print(f"{'='*70}")
            print(f"Total Trades:        {total_trades}")
            print(f"Win Rate:            {win_rate:.1f}%")
            print(f"Total P&L:          ${total_pnl:,.2f}")
        
        print("="*70)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n❌ Backtest failed: {e}")


if __name__ == "__main__":
    main()

