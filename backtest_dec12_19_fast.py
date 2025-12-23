#!/usr/bin/env python3
"""
Fast Backtest - December 12-19, 2025
Simplified version that focuses on signal generation and trade identification
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime, timedelta
import pandas as pd
from config import Config
from alpaca_client import AlpacaClient
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.agents.base_agent import TradeDirection
from services.massive_price_feed import MassivePriceFeed
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.WARNING)  # Reduce logging noise
logger = logging.getLogger(__name__)

def main():
    """Run fast backtest"""
    start_date = datetime(2025, 12, 12)
    end_date = datetime(2025, 12, 19)
    
    print("="*60)
    print("OPTIONS TRADING BACKTEST - DEC 12-19, 2025")
    print("="*60)
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Tickers: {', '.join(Config.TICKERS)}")
    print(f"Options: 0-30 DTE, LONG→CALL, SHORT→PUT")
    print("="*60)
    print()
    
    # Initialize
    alpaca_client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    massive_feed = MassivePriceFeed()
    orchestrator = MultiAgentOrchestrator(alpaca_client)
    
    all_trades = []
    all_signals = []
    all_rejected = []
    
    # Backtest each trading day
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Skip weekends
            print(f"\n{'='*60}")
            print(f"BACKTESTING: {current_date.strftime('%Y-%m-%d %A')}")
            print(f"{'='*60}")
            
            day_trades = []
            day_signals = []
            
            for symbol in Config.TICKERS:
                try:
                    # Get historical bars
                    end = current_date
                    start = end - timedelta(days=60)
                    
                    bars = None
                    if massive_feed.is_available():
                        bars = massive_feed.get_daily_bars(symbol, start, end)
                    
                    if bars is None or bars.empty:
                        bars = alpaca_client.get_historical_bars(symbol, TimeFrame.Day, start, end)
                    
                    if bars.empty or len(bars) < 30:
                        all_rejected.append({
                            'symbol': symbol,
                            'date': current_date,
                            'reason': f'Insufficient data ({len(bars)} bars)'
                        })
                        continue
                    
                    # Get current price
                    if bars.empty:
                        continue
                    current_price = float(bars.iloc[-1]['close'])
                    
                    # Generate signal
                    intent = orchestrator.analyze_symbol(symbol, bars)
                    if not intent or intent.direction == TradeDirection.FLAT:
                        continue
                    
                    if intent.confidence < 0.6:
                        all_rejected.append({
                            'symbol': symbol,
                            'date': current_date,
                            'reason': f'Confidence too low ({intent.confidence:.2%})',
                            'direction': intent.direction.value
                        })
                        continue
                    
                    # Record signal
                    signal_info = {
                        'symbol': symbol,
                        'date': current_date,
                        'direction': intent.direction.value,
                        'confidence': intent.confidence,
                        'agent': intent.agent_name,
                        'current_price': current_price
                    }
                    day_signals.append(signal_info)
                    all_signals.append(signal_info)
                    
                    print(f"  ✅ {symbol}: {intent.direction.value} @ {intent.confidence:.2%} ({intent.agent_name})")
                    
                    # Determine option type
                    option_type = 'CALL' if intent.direction.value == 'LONG' else 'PUT'
                    
                    # For backtest, we'll record the trade setup
                    # (actual option selection would require historical options data)
                    trade = {
                        'symbol': symbol,
                        'date': current_date,
                        'option_type': option_type,
                        'direction': intent.direction.value,
                        'current_price': current_price,
                        'confidence': intent.confidence,
                        'agent': intent.agent_name,
                        'status': 'WOULD_EXECUTE'  # Would execute if options available
                    }
                    day_trades.append(trade)
                    all_trades.append(trade)
                    
                    print(f"    📊 WOULD TRADE: {symbol} {option_type} @ ${current_price:.2f}")
                    
                except Exception as e:
                    print(f"  ❌ {symbol}: Error - {e}")
                    all_rejected.append({
                        'symbol': symbol,
                        'date': current_date,
                        'reason': f'Error: {str(e)}'
                    })
            
            print(f"\n  Day Summary: {len(day_signals)} signals, {len(day_trades)} trades")
        
        current_date += timedelta(days=1)
    
    # Generate report
    print(f"\n{'='*60}")
    print("BACKTEST RESULTS SUMMARY")
    print(f"{'='*60}\n")
    
    total_signals = len(all_signals)
    total_trades = len(all_trades)
    total_rejected = len(all_rejected)
    
    long_signals = len([s for s in all_signals if s['direction'] == 'LONG'])
    short_signals = len([s for s in all_signals if s['direction'] == 'SHORT'])
    
    call_trades = len([t for t in all_trades if t['option_type'] == 'CALL'])
    put_trades = len([t for t in all_trades if t['option_type'] == 'PUT'])
    
    print(f"📊 STATISTICS:")
    print(f"   Total Signals Generated: {total_signals}")
    print(f"     - LONG: {long_signals}")
    print(f"     - SHORT: {short_signals}")
    print(f"   Total Trades Would Execute: {total_trades}")
    print(f"     - CALL: {call_trades}")
    print(f"     - PUT: {put_trades}")
    print(f"   Total Rejected: {total_rejected}")
    print()
    
    # Trades by day
    print(f"📅 TRADES BY DAY:")
    trades_by_day = {}
    for trade in all_trades:
        day = trade['date'].strftime('%Y-%m-%d')
        if day not in trades_by_day:
            trades_by_day[day] = []
        trades_by_day[day].append(trade)
    
    for day in sorted(trades_by_day.keys()):
        day_trades = trades_by_day[day]
        print(f"   {day}: {len(day_trades)} trades")
        for trade in day_trades:
            print(f"      • {trade['symbol']} {trade['option_type']} @ ${trade['current_price']:.2f} ({trade['confidence']:.2%})")
    
    print()
    
    # Detailed trades
    print(f"📋 DETAILED TRADES:")
    for i, trade in enumerate(all_trades, 1):
        print(f"   {i}. {trade['date'].strftime('%Y-%m-%d')} | {trade['symbol']} | {trade['option_type']}")
        print(f"      Signal: {trade['direction']} @ {trade['confidence']:.2%} ({trade['agent']})")
        print(f"      Stock Price: ${trade['current_price']:.2f}")
        print(f"      Would Buy: {trade['option_type']} options (0-30 DTE, ATM)")
        print()
    
    # Rejection summary
    print(f"❌ TOP REJECTION REASONS:")
    rejection_reasons = {}
    for reject in all_rejected:
        reason = reject['reason']
        if reason not in rejection_reasons:
            rejection_reasons[reason] = 0
        rejection_reasons[reason] += 1
    
    for reason, count in sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   {reason}: {count}")
    
    # Save to file
    report_file = Path("backtest_results") / f"backtest_dec12_19_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w') as f:
        f.write("="*60 + "\n")
        f.write("OPTIONS TRADING BACKTEST REPORT\n")
        f.write(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")
        f.write("="*60 + "\n\n")
        
        f.write(f"Total Signals: {total_signals} (LONG: {long_signals}, SHORT: {short_signals})\n")
        f.write(f"Total Trades: {total_trades} (CALL: {call_trades}, PUT: {put_trades})\n")
        f.write(f"Total Rejected: {total_rejected}\n\n")
        
        f.write("TRADES:\n")
        f.write("-"*60 + "\n")
        for trade in all_trades:
            f.write(f"{trade['date'].strftime('%Y-%m-%d')} | {trade['symbol']} | {trade['option_type']} | ")
            f.write(f"${trade['current_price']:.2f} | {trade['direction']} @ {trade['confidence']:.2%} | {trade['agent']}\n")
    
    print(f"\n📄 Report saved to: {report_file}")

if __name__ == '__main__':
    main()

