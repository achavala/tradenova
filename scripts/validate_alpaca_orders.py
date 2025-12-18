#!/usr/bin/env python3
"""
Validate Alpaca Orders - Check if any orders were placed today
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from alpaca_client import AlpacaClient
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_alpaca_orders():
    """Validate orders in Alpaca account"""
    print("\n" + "="*70)
    print("ALPACA ORDERS VALIDATION - December 15, 2025")
    print("="*70)
    
    try:
        # Initialize client
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        print("\n1️⃣ Account Status:")
        print("-" * 70)
        account = client.get_account()
        print(f"✅ Account Connected Successfully")
        print(f"   Account ID: {account.get('account_number', 'N/A')}")
        print(f"   Equity: ${float(account['equity']):,.2f}")
        print(f"   Buying Power: ${float(account['buying_power']):,.2f}")
        print(f"   Cash: ${float(account['cash']):,.2f}")
        
        # Get today's date
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        print(f"\n2️⃣ Orders from Today ({today}):")
        print("-" * 70)
        
        # Get all orders
        try:
            all_orders = client.api.list_orders(
                status='all',
                limit=100,
                nested=True
            )
            
            today_orders = []
            for order in all_orders:
                # Handle both string and datetime objects
                if isinstance(order.submitted_at, str):
                    order_time = datetime.fromisoformat(order.submitted_at.replace('Z', '+00:00'))
                else:
                    order_time = order.submitted_at
                
                if hasattr(order_time, 'date'):
                    order_date = order_time.date()
                else:
                    order_date = order_time
                
                if order_date == today:
                    today_orders.append(order)
            
            if today_orders:
                print(f"✅ Found {len(today_orders)} order(s) from today:")
                for i, order in enumerate(today_orders, 1):
                    print(f"\n   Order {i}:")
                    print(f"     Symbol: {order.symbol}")
                    print(f"     Side: {order.side}")
                    print(f"     Qty: {order.qty}")
                    print(f"     Type: {order.order_type}")
                    print(f"     Status: {order.status}")
                    print(f"     Filled Qty: {order.filled_qty}")
                    if order.filled_avg_price:
                        print(f"     Avg Fill Price: ${float(order.filled_avg_price):.2f}")
                    print(f"     Submitted: {order.submitted_at}")
                    if order.filled_at:
                        print(f"     Filled: {order.filled_at}")
            else:
                print(f"❌ NO ORDERS from today ({today})")
                print(f"   Total orders in account: {len(all_orders)}")
                
                # Show recent orders
                if all_orders:
                    print(f"\n   Recent orders (last 5):")
                    for order in sorted(all_orders, key=lambda x: x.submitted_at, reverse=True)[:5]:
                        order_time = datetime.fromisoformat(order.submitted_at.replace('Z', '+00:00'))
                        print(f"     - {order.symbol} {order.side} {order.qty} @ {order.order_type} "
                              f"({order.status}) - {order_time.strftime('%Y-%m-%d %H:%M')}")
        
        except Exception as e:
            print(f"❌ Error fetching orders: {e}")
            logger.error(f"Error fetching orders: {e}", exc_info=True)
        
        print(f"\n3️⃣ Current Positions:")
        print("-" * 70)
        positions = client.get_positions()
        if positions:
            print(f"✅ {len(positions)} open position(s):")
            for pos in positions:
                pnl_sign = '+' if float(pos['unrealized_pl']) >= 0 else ''
                print(f"   {pos['symbol']:8s}: {pos['qty']:8.2f} @ ${float(pos['avg_entry_price']):7.2f} | "
                      f"P&L: {pnl_sign}${float(pos['unrealized_pl']):10,.2f}")
        else:
            print("❌ NO open positions")
        
        print(f"\n4️⃣ Order Execution Analysis:")
        print("-" * 70)
        
        # Check if trading system is running
        import subprocess
        result = subprocess.run(['pgrep', '-f', 'run_daily.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"✅ Trading system is RUNNING (PIDs: {', '.join(pids)})")
        else:
            print("❌ Trading system is NOT running")
            print("   This explains why no orders were placed!")
            return
        
        # Check recent logs for order execution attempts
        print(f"\n5️⃣ Recent Trading Activity (from logs):")
        print("-" * 70)
        
        log_files = [
            Path('logs/trading_today.log'),
            Path('logs/tradenova_daily.log'),
            Path('logs/trading_restart.log')
        ]
        
        found_activity = False
        for log_file in log_files:
            if log_file.exists():
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    # Look for order-related activity in last 50 lines
                    for line in lines[-50:]:
                        if any(keyword in line.lower() for keyword in [
                            'order', 'execute', 'trade', 'buy', 'sell', 
                            'position', 'signal', 'unauthorized', 'error'
                        ]):
                            if 'unauthorized' in line.lower():
                                print(f"   ⚠️  {log_file.name}: {line.strip()[:100]}")
                                found_activity = True
                            elif 'order' in line.lower() or 'execute' in line.lower():
                                print(f"   📋 {log_file.name}: {line.strip()[:100]}")
                                found_activity = True
        
        if not found_activity:
            print("   ⚠️  No recent order execution activity in logs")
        
        print(f"\n6️⃣ Root Cause Analysis:")
        print("-" * 70)
        
        if not today_orders:
            print("❌ NO ORDERS PLACED TODAY")
            print("\n   Possible reasons:")
            print("   1. Authentication error (unauthorized) - CHECK LOGS")
            print("   2. Trading system not executing orders")
            print("   3. Signals generated but not meeting execution criteria")
            print("   4. Risk management blocking trades")
            print("   5. Market conditions not suitable")
            
            # Check for authentication errors
            auth_errors = False
            for log_file in log_files:
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        if 'unauthorized' in f.read().lower():
                            auth_errors = True
                            break
            
            if auth_errors:
                print("\n   🔴 PRIMARY ISSUE: Authentication errors detected!")
                print("      - Trading system cannot authenticate with Alpaca")
                print("      - Run: ./scripts/fix_trading_auth.sh")
            else:
                print("\n   ⚠️  No authentication errors found in logs")
                print("      - Check signal generation and execution logic")
        
        print("\n" + "="*70)
        print("VALIDATION COMPLETE")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.error(f"Validation error: {e}", exc_info=True)


if __name__ == "__main__":
    validate_alpaca_orders()

