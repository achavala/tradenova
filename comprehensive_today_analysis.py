#!/usr/bin/env python3
"""
Comprehensive analysis of today's trading activity
Combines Alpaca data, log analysis, and signal/rejection tracking
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from alpaca_client import AlpacaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_comprehensive():
    """Comprehensive analysis"""
    print("="*80)
    print("TRADENOVA - COMPREHENSIVE TODAY'S ANALYSIS")
    print("="*80)
    print(f"Date: {date.today()}")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print("="*80)
    
    # Initialize Alpaca client
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    # Get account info
    account = client.get_account()
    print(f"\n📊 ACCOUNT STATUS")
    print(f"  Equity: ${float(account.get('equity', 0)):,.2f}")
    print(f"  Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
    print(f"  Cash: ${float(account.get('cash', 0)):,.2f}")
    
    # Get positions
    positions = client.get_positions()
    print(f"\n📈 CURRENT POSITIONS")
    print(f"  Total: {len(positions)}")
    
    stock_positions = []
    option_positions = []
    
    if positions:
        for pos in positions:
            symbol = pos.get('symbol', 'N/A')
            qty = pos.get('qty', 0)
            entry = pos.get('avg_entry_price', 0)
            current = pos.get('current_price', 0)
            pnl = pos.get('unrealized_pl', 0)
            asset_class = pos.get('asset_class', '')
            
            # Check if option (options have longer symbols, contain C/P, or asset_class='option')
            is_option = (
                asset_class == 'option' or 
                'C' in symbol or 
                'P' in symbol or 
                len(symbol) > 6
            )
            
            if is_option:
                option_positions.append(pos)
                print(f"  ✅ {symbol} (OPTION): {qty} @ ${entry:.2f} (current: ${current:.2f}, P&L: ${pnl:.2f})")
            else:
                stock_positions.append(pos)
                print(f"  ⚠️  {symbol} (STOCK): {qty} @ ${entry:.2f} (current: ${current:.2f}, P&L: ${pnl:.2f})")
    else:
        print("  No open positions")
    
    if stock_positions:
        print(f"\n⚠️  WARNING: Found {len(stock_positions)} STOCK positions!")
        print("  System should ONLY trade 0-30 DTE OPTIONS, not stocks.")
        print("  These may be from old trading logic or manual trades.")
    
    # Get orders from today
    today = date.today().isoformat()
    orders = client.get_orders(limit=100, status='all')
    
    today_orders = []
    for order in orders:
        created = order.get('created_at', '')
        if isinstance(created, str) and today in created:
            today_orders.append(order)
    
    print(f"\n📋 ORDERS TODAY")
    print(f"  Total: {len(today_orders)}")
    
    stock_orders = []
    option_orders = []
    
    if today_orders:
        for order in today_orders:
            symbol = order.get('symbol', 'N/A')
            side = order.get('side', 'N/A')
            qty = order.get('qty', 0)
            status = order.get('status', 'N/A')
            order_type = order.get('order_type', 'N/A')
            filled_price = order.get('filled_avg_price', 'N/A')
            created = order.get('created_at', 'N/A')
            asset_class = order.get('asset_class', '')
            
            # Check if option
            is_option = (
                asset_class == 'option' or 
                'C' in symbol or 
                'P' in symbol or 
                len(symbol) > 6
            )
            
            if is_option:
                option_orders.append(order)
                print(f"  ✅ {symbol} (OPTION): {side} {qty} @ ${filled_price} - {status} - {created}")
            else:
                stock_orders.append(order)
                print(f"  ⚠️  {symbol} (STOCK): {side} {qty} @ ${filled_price} - {status} - {created}")
    else:
        print("  No orders placed today")
    
    if stock_orders:
        print(f"\n⚠️  WARNING: Found {len(stock_orders)} STOCK orders today!")
        print("  System should ONLY trade 0-30 DTE OPTIONS, not stocks.")
    
    # Analysis summary
    print(f"\n🔍 ANALYSIS SUMMARY")
    print(f"  Stock positions: {len(stock_positions)}")
    print(f"  Option positions: {len(option_positions)}")
    print(f"  Stock orders today: {len(stock_orders)}")
    print(f"  Option orders today: {len(option_orders)}")
    
    # Check dashboard data source
    print(f"\n📊 DASHBOARD DATA SOURCE")
    print("  Dashboard loads trades from:")
    print("    1. Backtest results (JSON files in logs/)")
    print("    2. Live Alpaca orders")
    print("  ⚠️  If you see 'stocks with today's date', they may be:")
    print("     - From backtest results (now filtered out)")
    print("     - From old stock trading logic (before options-only fix)")
    print("     - From manual trades")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    
    if len(today_orders) == 0:
        print("  ⚠️  NO TRADES EXECUTED TODAY")
        print("  Possible reasons:")
        print("    1. No signals generated (check confidence threshold ≥ 70%)")
        print("    2. All signals rejected by risk management")
        print("    3. No liquid options found (liquidity filter)")
        print("    4. Market was closed or system wasn't running")
        print("    5. Position limit reached (MAX_ACTIVE_TRADES)")
        print("  → Check Fly.io logs for detailed signal/rejection information")
    
    if stock_positions or stock_orders:
        print("  ⚠️  STOCK TRADES DETECTED")
        print("  → System should ONLY trade 0-30 DTE OPTIONS")
        print("  → Verify old stock trading logic is disabled")
        print("  → Check if these are from manual trades")
    
    if len(option_orders) == 0 and len(today_orders) == 0:
        print("  ✅ No option trades today (expected if no valid setups)")
        print("  → System is correctly configured for options-only trading")
        print("  → Check logs for signal generation and rejection reasons")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("  1. Check Fly.io logs: flyctl logs --app tradenova")
    print("  2. Look for 'Signal found' and 'Trade BLOCKED' messages")
    print("  3. Review rejection reasons")
    print("  4. Verify system is running: flyctl status --app tradenova")

if __name__ == '__main__':
    analyze_comprehensive()




