#!/usr/bin/env python3
"""
Validate Trades Today - Check if trades were picked and why they might have been rejected
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

from config import Config
from alpaca_client import AlpacaClient
from alpaca_trade_api.rest import TimeFrame
from core.multi_agent_orchestrator import MultiAgentOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_market_status():
    """Check if market is open"""
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        is_open = client.is_market_open()
        account = client.get_account()
        return {
            'market_open': is_open,
            'equity': float(account['equity']),
            'buying_power': float(account['buying_power']),
            'positions': client.get_positions()
        }
    except Exception as e:
        logger.error(f"Error checking market status: {e}")
        return None


def analyze_signals_for_today():
    """Analyze what signals were generated today and why trades might have been rejected"""
    print("\n" + "="*70)
    print("TRADE VALIDATION - TODAY'S ANALYSIS")
    print("="*70)
    
    # Check market status
    print("\n📊 Market Status:")
    print("-" * 70)
    market_info = check_market_status()
    if market_info:
        print(f"Market Open: {'✅ YES' if market_info['market_open'] else '❌ NO'}")
        print(f"Account Equity: ${market_info['equity']:,.2f}")
        print(f"Buying Power: ${market_info['buying_power']:,.2f}")
        print(f"Open Positions: {len(market_info['positions'])}")
        
        if market_info['positions']:
            print("\nCurrent Positions:")
            for pos in market_info['positions']:
                pnl_sign = '+' if pos['unrealized_pl'] >= 0 else ''
                print(f"  {pos['symbol']:6s}: {pos['qty']:6.0f} @ ${pos['avg_entry_price']:7.2f} | "
                      f"P&L: {pnl_sign}${pos['unrealized_pl']:8,.2f}")
    else:
        print("❌ Could not check market status")
        return
    
    if not market_info['market_open']:
        print("\n⚠️  Market is currently closed. Analysis will use latest available data.")
    
    # Initialize orchestrator
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        orchestrator = MultiAgentOrchestrator(client)
    except Exception as e:
        print(f"\n❌ Error initializing orchestrator: {e}")
        return
    
    # Get today's date
    today = datetime.now().date()
    
    # Fetch data for analysis
    print(f"\n🔍 Analyzing Signals for {today}:")
    print("-" * 70)
    
    signals_generated = []
    signals_rejected = []
    
    # Get data for each ticker
    for ticker in Config.TICKERS:
        try:
            # Get last 90 days of data for analysis
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            bars = client.get_historical_bars(ticker, TimeFrame.Day, start_date, end_date)
            if bars.empty or len(bars) < 50:
                continue
            
            # Analyze with orchestrator
            trade_intent = orchestrator.analyze_symbol(ticker, bars)
            
            if trade_intent:
                signal_info = {
                    'symbol': ticker,
                    'direction': trade_intent.direction.value,
                    'confidence': trade_intent.confidence,
                    'agent': trade_intent.agent_name,
                    'reasoning': trade_intent.reasoning,
                    'timestamp': datetime.now()
                }
                signals_generated.append(signal_info)
                
                # Check why it might be rejected
                rejection_reasons = []
                
                # Check confidence threshold
                if trade_intent.confidence < 0.20:
                    rejection_reasons.append(f"Confidence too low ({trade_intent.confidence:.2f} < 0.20)")
                
                # Check if position already exists
                if market_info['positions']:
                    existing_symbols = [p['symbol'] for p in market_info['positions']]
                    if ticker in existing_symbols:
                        rejection_reasons.append(f"Position already exists for {ticker}")
                
                # Check max positions
                if len(market_info['positions']) >= Config.MAX_ACTIVE_TRADES:
                    rejection_reasons.append(f"Max positions reached ({len(market_info['positions'])}/{Config.MAX_ACTIVE_TRADES})")
                
                if rejection_reasons:
                    signal_info['rejection_reasons'] = rejection_reasons
                    signals_rejected.append(signal_info)
                else:
                    print(f"✅ {ticker}: {trade_intent.direction.value} signal from {trade_intent.agent_name} "
                          f"(confidence: {trade_intent.confidence:.2f}) - WOULD EXECUTE")
            else:
                logger.debug(f"{ticker}: No signal generated")
        
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            continue
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print(f"\n📊 Signals Generated: {len(signals_generated)}")
    print(f"✅ Signals That Would Execute: {len(signals_generated) - len(signals_rejected)}")
    print(f"❌ Signals Rejected: {len(signals_rejected)}")
    
    if signals_rejected:
        print(f"\n❌ Rejected Signals:")
        print("-" * 70)
        for sig in signals_rejected:
            print(f"\n{sig['symbol']}: {sig['direction']} from {sig['agent']} (confidence: {sig['confidence']:.2f})")
            for reason in sig.get('rejection_reasons', []):
                print(f"  - {reason}")
    
    if signals_generated and not signals_rejected:
        print("\n✅ All signals would execute! Check if trading system is running.")
    
    if not signals_generated:
        print("\n⚠️  No signals generated. Possible reasons:")
        print("  - Market conditions don't meet criteria")
        print("  - Regime confidence too low (< 0.30)")
        print("  - Agents not finding suitable opportunities")
        print("  - Insufficient historical data")
    
    # Check trading system status
    print("\n" + "="*70)
    print("TRADING SYSTEM STATUS")
    print("="*70)
    
    # Check if run_daily.py is running
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'run_daily.py'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        pids = result.stdout.strip().split('\n')
        print(f"✅ Trading system is RUNNING (PIDs: {', '.join(pids)})")
    else:
        print("❌ Trading system is NOT running")
        print("   Start with: python run_daily.py --paper")
    
    # Check logs
    log_file = Path('logs/trading_today.log')
    if log_file.exists():
        print(f"\n📋 Recent Log Activity:")
        print("-" * 70)
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Get last 20 lines
            for line in lines[-20:]:
                if any(keyword in line.lower() for keyword in ['trade', 'signal', 'execute', 'reject', 'block', 'market open']):
                    print(line.strip())
    
    print("\n" + "="*70)


if __name__ == "__main__":
    analyze_signals_for_today()





