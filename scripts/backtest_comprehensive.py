#!/usr/bin/env python3
"""
Comprehensive Backtest - Tests RL and All Agents
Verifies that trades are being picked by RL and other agents
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
    """Run comprehensive backtest"""
    print("\n" + "="*70)
    print("COMPREHENSIVE BACKTEST - RL & Multi-Agent System")
    print("="*70)
    
    # Use 90 days to get enough data for RL/agents (need 50+ bars)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Use all tickers
    tickers = Config.TICKERS[:6]  # Test with first 6 for faster results
    
    print(f"\n📅 Date Range: {start_date.date()} to {end_date.date()}")
    print(f"📊 Tickers: {', '.join(tickers)}")
    print(f"💰 Initial Balance: $100,000")
    print(f"\n🔍 Testing:")
    print(f"  - Multi-Agent Orchestrator")
    print(f"  - RL Agents (if available)")
    print(f"  - All 8 trading agents")
    print(f"  - Signal generation")
    print(f"  - Trade execution")
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
    
    try:
        engine.run_backtest()
        
        # Analyze results
        print("\n" + "="*70)
        print("BACKTEST RESULTS ANALYSIS")
        print("="*70)
        
        total_trades = len(engine.trades)
        print(f"\n📊 Total Trades: {total_trades}")
        
        if total_trades > 0:
            print(f"\n✅ SUCCESS: Trades are being picked!")
            
            # Analyze by agent
            agent_stats = {}
            for trade in engine.trades:
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
            
            print(f"\n📈 Trades by Agent:")
            print(f"{'='*70}")
            for agent, stats in sorted(agent_stats.items(), key=lambda x: x[1]['count'], reverse=True):
                win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
                print(f"{agent:20s}: {stats['count']:3d} trades | "
                      f"Win Rate: {win_rate:5.1f}% | "
                      f"P&L: ${stats['total_pnl']:8,.2f}")
            
            # Check for RL agents
            rl_agents = [a for a in agent_stats.keys() if 'RL' in a or 'GRPO' in a or 'PPO' in a]
            if rl_agents:
                print(f"\n🤖 RL Agents Active: {', '.join(rl_agents)}")
            else:
                print(f"\n⚠️  No RL agents found in trades (may be using other agents)")
            
            # Show sample trades
            print(f"\n📋 Sample Trades (First 10):")
            print(f"{'='*70}")
            for i, trade in enumerate(engine.trades[:10], 1):
                entry_date = pd.to_datetime(trade['entry_time']).strftime('%Y-%m-%d')
                exit_date = pd.to_datetime(trade['exit_time']).strftime('%Y-%m-%d') if trade.get('exit_time') else 'Open'
                pnl_sign = '+' if trade['pnl'] >= 0 else ''
                print(f"{i:2d}. {trade['symbol']:6s} | {entry_date} → {exit_date} | "
                      f"{pnl_sign}${trade['pnl']:7,.2f} ({pnl_sign}{trade['pnl_pct']:.2f}%) | "
                      f"Agent: {trade.get('agent', 'Unknown')}")
            
            # Performance summary
            winning_trades = [t for t in engine.trades if t['pnl'] > 0]
            losing_trades = [t for t in engine.trades if t['pnl'] <= 0]
            win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
            total_pnl = sum(t['pnl'] for t in engine.trades)
            
            print(f"\n💰 Performance Summary:")
            print(f"{'='*70}")
            print(f"Total Trades:        {total_trades}")
            print(f"Winning Trades:      {len(winning_trades)}")
            print(f"Losing Trades:       {len(losing_trades)}")
            print(f"Win Rate:            {win_rate:.2f}%")
            print(f"Total P&L:          ${total_pnl:,.2f}")
            print(f"Final Balance:      ${engine.current_balance:,.2f}")
            print(f"Return:              {((engine.current_balance - 100000) / 100000 * 100):.2f}%")
            
        else:
            print(f"\n⚠️  No trades were picked.")
            print(f"\nPossible reasons:")
            print(f"  - Signal confidence thresholds too high")
            print(f"  - Regime confidence too low")
            print(f"  - Insufficient historical data")
            print(f"  - Market conditions didn't meet criteria")
            print(f"  - RL models not trained yet")
        
        print("="*70)
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        print(f"\n❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()





