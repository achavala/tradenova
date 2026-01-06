#!/usr/bin/env python3
"""
Check Trades Today - Comprehensive report of trades executed and signals generated
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

logging.basicConfig(level=logging.WARNING)  # Suppress info logs
logger = logging.getLogger(__name__)


def check_trades_today():
    """Check if any trades were executed today"""
    print("\n" + "="*80)
    print("TRADES EXECUTION REPORT - December 15, 2025".center(80))
    print("="*80)
    
    today = datetime.now().date()
    
    # 1. Check Alpaca for executed orders
    print("\n1️⃣ CHECKING ALPACA FOR EXECUTED ORDERS")
    print("-" * 80)
    
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        # Get all orders
        all_orders = client.api.list_orders(status='all', limit=100, nested=True)
        
        # Filter for today's orders
        today_orders = []
        for order in all_orders:
            # Parse order time
            if isinstance(order.submitted_at, str):
                order_time = pd.to_datetime(order.submitted_at)
            else:
                order_time = order.submitted_at
            
            if hasattr(order_time, 'date'):
                order_date = order_time.date()
            else:
                order_date = pd.to_datetime(order_time).date()
            
            if order_date == today:
                today_orders.append(order)
        
        if today_orders:
            print(f"✅ FOUND {len(today_orders)} TRADE(S) EXECUTED TODAY:\n")
            for i, order in enumerate(today_orders, 1):
                print(f"   Trade {i}:")
                print(f"     Symbol: {order.symbol}")
                print(f"     Side: {order.side.upper()}")
                print(f"     Quantity: {order.qty}")
                print(f"     Order Type: {order.order_type}")
                print(f"     Status: {order.status}")
                if order.filled_qty:
                    print(f"     Filled: {order.filled_qty} / {order.qty}")
                if order.filled_avg_price:
                    print(f"     Avg Fill Price: ${float(order.filled_avg_price):.2f}")
                print(f"     Submitted: {order.submitted_at}")
                if order.filled_at:
                    print(f"     Filled At: {order.filled_at}")
                print()
            
            # Summary
            buy_orders = [o for o in today_orders if o.side.lower() == 'buy']
            sell_orders = [o for o in today_orders if o.side.lower() == 'sell']
            filled_orders = [o for o in today_orders if o.status == 'filled']
            
            print(f"   Summary:")
            print(f"     - Buy Orders: {len(buy_orders)}")
            print(f"     - Sell Orders: {len(sell_orders)}")
            print(f"     - Filled Orders: {len(filled_orders)}")
            
            return True  # Trades were executed
            
        else:
            print(f"❌ NO TRADES EXECUTED TODAY ({today})")
            print(f"   Total orders in account: {len(all_orders)}")
            
            if all_orders:
                print(f"\n   Last order was on:")
                last_order = sorted(all_orders, key=lambda x: x.submitted_at, reverse=True)[0]
                if isinstance(last_order.submitted_at, str):
                    last_time = pd.to_datetime(last_order.submitted_at)
                else:
                    last_time = last_order.submitted_at
                print(f"     {last_order.symbol} {last_order.side} {last_order.qty} - {last_time}")
            
            return False  # No trades executed
    
    except Exception as e:
        print(f"❌ Error checking Alpaca: {e}")
        return False
    
    # 2. Check signals generated
    print("\n2️⃣ CHECKING SIGNALS GENERATED TODAY")
    print("-" * 80)
    
    try:
        orchestrator = MultiAgentOrchestrator(client)
        
        signals = []
        for ticker in Config.TICKERS:
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                
                bars = client.get_historical_bars(ticker, TimeFrame.Day, start_date, end_date)
                if bars.empty or len(bars) < 50:
                    continue
                
                trade_intent = orchestrator.analyze_symbol(ticker, bars)
                
                if trade_intent and trade_intent.confidence >= 0.20:
                    signals.append({
                        'symbol': ticker,
                        'direction': trade_intent.direction.value,
                        'confidence': trade_intent.confidence,
                        'agent': trade_intent.agent_name,
                        'reasoning': trade_intent.reasoning
                    })
            except Exception as e:
                logger.debug(f"Error analyzing {ticker}: {e}")
                continue
        
        if signals:
            print(f"✅ FOUND {len(signals)} SIGNAL(S) GENERATED:\n")
            for i, sig in enumerate(signals, 1):
                print(f"   Signal {i}:")
                print(f"     Symbol: {sig['symbol']}")
                print(f"     Direction: {sig['direction']}")
                print(f"     Confidence: {sig['confidence']:.2f}")
                print(f"     Agent: {sig['agent']}")
                print(f"     Reasoning: {sig['reasoning'][:100]}...")
                print()
        else:
            print("❌ NO SIGNALS GENERATED TODAY")
    
    except Exception as e:
        print(f"❌ Error checking signals: {e}")
    
    # 3. Check why trades weren't executed
    print("\n3️⃣ REASON ANALYSIS - WHY TRADES WEREN'T EXECUTED")
    print("-" * 80)
    
    reasons = []
    
    # Check authentication
    import subprocess
    log_files = [
        Path('logs/trading_today.log'),
        Path('logs/tradenova_daily.log')
    ]
    
    auth_error = False
    for log_file in log_files:
        if log_file.exists():
            with open(log_file, 'r') as f:
                content = f.read()
                if 'unauthorized' in content.lower():
                    auth_error = True
                    reasons.append("🔴 Authentication Error: Trading system cannot authenticate with Alpaca API")
                    break
    
    # Check if trading system is running
    result = subprocess.run(['pgrep', '-f', 'run_daily.py'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        pids = result.stdout.strip().split('\n')
        print(f"✅ Trading system is RUNNING (PIDs: {', '.join(pids)})")
    else:
        reasons.append("🔴 Trading System Not Running: No trading process found")
        print("❌ Trading system is NOT running")
    
    # Check signals vs execution
    if signals and not today_orders:
        if auth_error:
            reasons.append(f"⚠️  {len(signals)} signals generated but blocked by authentication error")
        else:
            reasons.append(f"⚠️  {len(signals)} signals generated but not executed (check risk management)")
    
    # Check risk management
    if signals:
        high_confidence = [s for s in signals if s['confidence'] >= 0.60]
        if high_confidence and not today_orders:
            reasons.append(f"⚠️  {len(high_confidence)} high-confidence signals (≥0.60) not executed")
    
    # Print reasons
    if reasons:
        print("\n   Reasons why trades weren't executed:")
        for i, reason in enumerate(reasons, 1):
            print(f"   {i}. {reason}")
    else:
        print("   ✅ No blocking issues found")
    
    # 4. System Status
    print("\n4️⃣ SYSTEM STATUS")
    print("-" * 80)
    
    try:
        account = client.get_account()
        positions = client.get_positions()
        is_open = client.is_market_open()
        
        print(f"   Market Status: {'✅ OPEN' if is_open else '❌ CLOSED'}")
        print(f"   Account Equity: ${float(account['equity']):,.2f}")
        print(f"   Buying Power: ${float(account['buying_power']):,.2f}")
        print(f"   Open Positions: {len(positions)}")
        
        if positions:
            print(f"\n   Current Positions:")
            for pos in positions:
                pnl_sign = '+' if float(pos['unrealized_pl']) >= 0 else ''
                print(f"     {pos['symbol']:8s}: {pos['qty']:8.2f} @ ${float(pos['avg_entry_price']):7.2f} | "
                      f"P&L: {pnl_sign}${float(pos['unrealized_pl']):10,.2f}")
    
    except Exception as e:
        print(f"   ⚠️  Could not get system status: {e}")
    
    # 5. Summary
    print("\n" + "="*80)
    print("SUMMARY".center(80))
    print("="*80)
    
    if today_orders:
        print(f"\n✅ TRADES EXECUTED: {len(today_orders)}")
        print(f"   ✅ System is working correctly")
    else:
        print(f"\n❌ TRADES EXECUTED: 0")
        if signals:
            print(f"   ⚠️  Signals Generated: {len(signals)}")
            print(f"   ⚠️  Signals NOT executed due to:")
            for reason in reasons:
                print(f"      - {reason}")
        else:
            print(f"   ⚠️  No signals generated today")
            print(f"   ⚠️  Possible reasons:")
            print(f"      - Market conditions don't meet criteria")
            print(f"      - Regime confidence too low")
            print(f"      - Agents not finding suitable opportunities")
    
    print("\n" + "="*80)
    
    return {
        'trades_executed': len(today_orders) if 'today_orders' in locals() else 0,
        'signals_generated': len(signals) if 'signals' in locals() else 0,
        'reasons': reasons
    }


if __name__ == "__main__":
    check_trades_today()





