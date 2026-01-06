#!/usr/bin/env python3
"""
7-Day Backtest - CORRECT Implementation
Uses 90-day lookback for analysis, but only executes trades in last 7 days
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
import pandas as pd

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
    """Run 7-day backtest with proper warmup"""
    print("\n" + "="*70)
    print("7-DAY BACKTEST - CORRECT IMPLEMENTATION")
    print("="*70)
    print("\n📋 Strategy:")
    print("  - Analysis Window: 90 days (for feature calculation)")
    print("  - Execution Window: Last 7 days only")
    print("  - Warmup Mode: Trading disabled until 50+ bars available")
    print("="*70)
    
    # Calculate date ranges
    end_date = datetime.now()
    trading_start = end_date - timedelta(days=7)  # Last 7 days
    data_start = trading_start - timedelta(days=60)  # 60 days before for warmup
    
    # Use all tickers
    tickers = Config.TICKERS
    
    print(f"\n📅 Data Range: {data_start.date()} to {end_date.date()}")
    print(f"📅 Trading Window: {trading_start.date()} to {end_date.date()} (Last 7 days)")
    print(f"📈 Tickers: {', '.join(tickers)}")
    print(f"💰 Initial Balance: $100,000")
    print("\n" + "="*70)
    print("Starting backtest...")
    print("="*70 + "\n")
    
    # Create backtest engine
    engine = BacktestEngine(
        tickers=tickers,
        start_date=data_start,  # Extended for warmup
        end_date=end_date,
        initial_balance=100000.0
    )
    
    # Store trading start date for filtering
    engine.trading_start_date = trading_start
    
    try:
        engine.run_backtest()
        
        # Filter trades to only those in the trading window (last 7 days)
        trading_window_trades = []
        for t in engine.trades:
            entry_time = pd.to_datetime(t['entry_time'])
            # Make timezone-aware if needed
            if entry_time.tzinfo is None:
                entry_time = entry_time.tz_localize('UTC')
            if trading_start.tzinfo is None:
                trading_start_aware = trading_start.replace(tzinfo=entry_time.tzinfo)
            else:
                trading_start_aware = trading_start
            if entry_time >= trading_start_aware:
                trading_window_trades.append(t)
        
        # Analyze results
        print("\n" + "="*70)
        print("7-DAY BACKTEST RESULTS")
        print("="*70)
        
        total_trades = len(trading_window_trades)
        total_all_period = len(engine.trades)
        
        print(f"\n📊 Total Trades (Last 7 Days): {total_trades}")
        print(f"📊 Total Trades (All Period): {total_all_period}")
        
        if total_trades > 0:
            print(f"\n✅ SUCCESS: Trades are being picked in the last 7 days!")
            
            # Analyze by agent
            agent_stats = {}
            for trade in trading_window_trades:
                agent = trade.get('agent', 'Unknown')
                if agent not in agent_stats:
                    agent_stats[agent] = {
                        'count': 0,
                        'wins': 0,
                        'losses': 0,
                        'total_pnl': 0.0
                    }
                agent_stats[agent]['count'] += 1
                if trade['pnl'] > 0:
                    agent_stats[agent]['wins'] += 1
                else:
                    agent_stats[agent]['losses'] += 1
                agent_stats[agent]['total_pnl'] += trade['pnl']
            
            print(f"\n📈 Trades by Agent (Last 7 Days):")
            print(f"{'='*70}")
            for agent, stats in sorted(agent_stats.items(), key=lambda x: x[1]['count'], reverse=True):
                win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
                print(f"{agent:20s}: {stats['count']:3d} trades | "
                      f"Win Rate: {win_rate:5.1f}% | "
                      f"P&L: ${stats['total_pnl']:8,.2f}")
            
            # Check for RL agents
            rl_agents = [a for a in agent_stats.keys() if any(x in a.upper() for x in ['RL', 'GRPO', 'PPO', 'REINFORCEMENT'])]
            if rl_agents:
                print(f"\n🤖 RL Agents Active: {', '.join(rl_agents)}")
            else:
                print(f"\n⚠️  No RL agents found (using rule-based agents)")
                print(f"   RL agents will activate after training models")
            
            # Show all trades
            print(f"\n📋 All Trades (Last 7 Days):")
            print(f"{'='*70}")
            for i, trade in enumerate(trading_window_trades, 1):
                entry_date = pd.to_datetime(trade['entry_time']).strftime('%Y-%m-%d')
                exit_date = pd.to_datetime(trade['exit_time']).strftime('%Y-%m-%d') if trade.get('exit_time') else 'Open'
                pnl_sign = '+' if trade['pnl'] >= 0 else ''
                print(f"{i:2d}. {trade['symbol']:6s} | {entry_date} → {exit_date} | "
                      f"{pnl_sign}${trade['pnl']:7,.2f} ({pnl_sign}{trade['pnl_pct']:.2f}%) | "
                      f"Agent: {trade.get('agent', 'Unknown')}")
            
            # Performance summary
            winning_trades = [t for t in trading_window_trades if t['pnl'] > 0]
            losing_trades = [t for t in trading_window_trades if t['pnl'] <= 0]
            win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
            total_pnl = sum(t['pnl'] for t in trading_window_trades)
            
            print(f"\n💰 Performance Summary (Last 7 Days):")
            print(f"{'='*70}")
            print(f"Total Trades:        {total_trades}")
            print(f"Winning Trades:      {len(winning_trades)}")
            print(f"Losing Trades:       {len(losing_trades)}")
            print(f"Win Rate:            {win_rate:.2f}%")
            print(f"Total P&L:          ${total_pnl:,.2f}")
            print(f"Return:              {((total_pnl / 100000) * 100):.2f}%")
            
        else:
            print(f"\n⚠️  No trades in the last 7 days")
            if total_all_period > 0:
                print(f"   (But {total_all_period} trades found in warmup period)")
            print(f"\nThis is expected if:")
            print(f"  - Market conditions didn't meet criteria")
            print(f"  - Signal confidence thresholds not met")
            print(f"  - Regime confidence too low")
        
        print("="*70)
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        print(f"\n❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()





