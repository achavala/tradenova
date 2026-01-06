#!/usr/bin/env python3
"""
7-Day Backtest - Tests RL and All Agents
Verifies that trades are being picked by RL and other agents in the last 7 days
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
    """Run 7-day backtest"""
    print("\n" + "="*70)
    print("7-DAY BACKTEST - RL & Multi-Agent System")
    print("="*70)
    
    # Calculate date range (last 7 days)
    end_date = datetime.now()
    backtest_start = end_date - timedelta(days=7)
    
    # Need extended data range for analysis (agents need 50+ bars)
    # Get 90 days of data but only trade in last 7 days
    data_start = backtest_start - timedelta(days=60)
    
    # Use all tickers
    tickers = Config.TICKERS
    
    print(f"\n📅 Backtest Period: {backtest_start.date()} to {end_date.date()} (Last 7 days)")
    print(f"📊 Data Range: {data_start.date()} to {end_date.date()} (extended for analysis)")
    print(f"📈 Tickers: {', '.join(tickers)}")
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
    
    # Create backtest engine with extended data range
    engine = BacktestEngine(
        tickers=tickers,
        start_date=data_start,  # Extended for analysis
        end_date=end_date,
        initial_balance=100000.0
    )
    
    try:
        engine.run_backtest()
        
        # Filter trades to only those in the last 7 days
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
        
        # Analyze results
        print("\n" + "="*70)
        print("7-DAY BACKTEST RESULTS")
        print("="*70)
        
        total_trades = len(backtest_trades)
        print(f"\n📊 Total Trades (Last 7 Days): {total_trades}")
        print(f"📊 Total Trades (All Data): {len(engine.trades)}")
        
        if total_trades > 0:
            print(f"\n✅ SUCCESS: Trades are being picked in the last 7 days!")
            
            # Analyze by agent
            agent_stats = {}
            for trade in backtest_trades:
                agent = trade.get('agent', 'Unknown')
                if agent not in agent_stats:
                    agent_stats[agent] = {
                        'count': 0,
                        'wins': 0,
                        'losses': 0,
                        'total_pnl': 0.0,
                        'avg_confidence': 0.0,
                        'confidences': []
                    }
                agent_stats[agent]['count'] += 1
                if trade['pnl'] > 0:
                    agent_stats[agent]['wins'] += 1
                else:
                    agent_stats[agent]['losses'] += 1
                agent_stats[agent]['total_pnl'] += trade['pnl']
                # Try to get confidence if available
                if 'confidence' in trade:
                    agent_stats[agent]['confidences'].append(trade['confidence'])
            
            # Calculate average confidence
            for agent in agent_stats:
                if agent_stats[agent]['confidences']:
                    agent_stats[agent]['avg_confidence'] = sum(agent_stats[agent]['confidences']) / len(agent_stats[agent]['confidences'])
            
            print(f"\n📈 Trades by Agent (Last 7 Days):")
            print(f"{'='*70}")
            for agent, stats in sorted(agent_stats.items(), key=lambda x: x[1]['count'], reverse=True):
                win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
                avg_conf = stats['avg_confidence'] * 100 if stats['avg_confidence'] > 0 else 0
                print(f"{agent:20s}: {stats['count']:3d} trades | "
                      f"Win Rate: {win_rate:5.1f}% | "
                      f"P&L: ${stats['total_pnl']:8,.2f} | "
                      f"Avg Conf: {avg_conf:.1f}%")
            
            # Check for RL agents
            rl_agents = [a for a in agent_stats.keys() if any(x in a.upper() for x in ['RL', 'GRPO', 'PPO', 'REINFORCEMENT'])]
            if rl_agents:
                print(f"\n🤖 RL Agents Active: {', '.join(rl_agents)}")
            else:
                print(f"\n⚠️  No RL agents found in trades")
                print(f"   (Using rule-based agents: VolatilityAgent, TrendAgent, etc.)")
                print(f"   RL agents will activate after training models")
            
            # Show all trades
            print(f"\n📋 All Trades (Last 7 Days):")
            print(f"{'='*70}")
            for i, trade in enumerate(backtest_trades, 1):
                entry_date = pd.to_datetime(trade['entry_time']).strftime('%Y-%m-%d')
                exit_date = pd.to_datetime(trade['exit_time']).strftime('%Y-%m-%d') if trade.get('exit_time') else 'Open'
                pnl_sign = '+' if trade['pnl'] >= 0 else ''
                confidence = trade.get('confidence', 0) * 100 if 'confidence' in trade else 0
                print(f"{i:2d}. {trade['symbol']:6s} | {entry_date} → {exit_date} | "
                      f"{pnl_sign}${trade['pnl']:7,.2f} ({pnl_sign}{trade['pnl_pct']:.2f}%) | "
                      f"Agent: {trade.get('agent', 'Unknown'):20s} | "
                      f"Conf: {confidence:.0f}%")
            
            # Performance summary
            winning_trades = [t for t in backtest_trades if t['pnl'] > 0]
            losing_trades = [t for t in backtest_trades if t['pnl'] <= 0]
            win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
            total_pnl = sum(t['pnl'] for t in backtest_trades)
            
            # Calculate balance change
            initial_for_period = 100000.0
            # Estimate final balance (simplified)
            final_balance = initial_for_period + total_pnl
            
            print(f"\n💰 Performance Summary (Last 7 Days):")
            print(f"{'='*70}")
            print(f"Total Trades:        {total_trades}")
            print(f"Winning Trades:      {len(winning_trades)}")
            print(f"Losing Trades:       {len(losing_trades)}")
            print(f"Win Rate:            {win_rate:.2f}%")
            print(f"Total P&L:          ${total_pnl:,.2f}")
            print(f"Estimated Return:    {((total_pnl / initial_for_period) * 100):.2f}%")
            
            if winning_trades:
                avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades)
                print(f"Average Win:         ${avg_win:,.2f}")
            if losing_trades:
                avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades)
                print(f"Average Loss:        ${avg_loss:,.2f}")
            
        else:
            print(f"\n⚠️  No trades were picked in the last 7 days.")
            print(f"\nPossible reasons:")
            print(f"  - Signal confidence thresholds too high (need >= 0.30)")
            print(f"  - Regime confidence too low (need >= 0.40)")
            print(f"  - Market conditions didn't meet criteria")
            print(f"  - RL models not trained yet")
            print(f"  - Not enough trading days (weekends/holidays)")
            
            # Show if trades were found in extended period
            if len(engine.trades) > 0:
                print(f"\n   Note: {len(engine.trades)} trades found in extended data range")
                print(f"   (but outside the 7-day window)")
        
        print("="*70)
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        print(f"\n❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()





