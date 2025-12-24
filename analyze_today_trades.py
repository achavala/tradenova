#!/usr/bin/env python3
"""
Detailed analysis of today's trading activity
Analyzes signals, rejections, and actual trades
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from alpaca_client import AlpacaClient
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_today():
    """Analyze today's trading activity"""
    print("="*80)
    print("TRADENOVA - TODAY'S TRADING ANALYSIS")
    print("="*80)
    print(f"Date: {date.today()}")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print("="*80)
    
    # Initialize Alpaca client
    from config import Config
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
    
    if positions:
        for pos in positions:
            symbol = pos.get('symbol', 'N/A')
            qty = pos.get('qty', 0)
            entry = pos.get('avg_entry_price', 0)
            current = pos.get('current_price', 0)
            pnl = pos.get('unrealized_pl', 0)
            print(f"  {symbol}: {qty} @ ${entry:.2f} (current: ${current:.2f}, P&L: ${pnl:.2f})")
    else:
        print("  No open positions")
    
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
    
    if today_orders:
        for order in today_orders:
            symbol = order.get('symbol', 'N/A')
            side = order.get('side', 'N/A')
            qty = order.get('qty', 0)
            status = order.get('status', 'N/A')
            order_type = order.get('order_type', 'N/A')
            filled_price = order.get('filled_avg_price', 'N/A')
            created = order.get('created_at', 'N/A')
            
            # Check if it's an option
            asset_class = order.get('asset_class', '')
            is_option = asset_class == 'option' or 'C' in symbol or 'P' in symbol or len(symbol) > 6
            
            print(f"  {symbol} ({'OPTION' if is_option else 'STOCK'}): {side} {qty} @ ${filled_price} - {status} - {created}")
    else:
        print("  No orders placed today")
    
    # Check for stock vs options
    print(f"\n🔍 ANALYSIS")
    
    stock_orders = [o for o in today_orders if not (o.get('asset_class') == 'option' or 'C' in o.get('symbol', '') or 'P' in o.get('symbol', '') or len(o.get('symbol', '')) > 6)]
    option_orders = [o for o in today_orders if o.get('asset_class') == 'option' or 'C' in o.get('symbol', '') or 'P' in o.get('symbol', '') or len(o.get('symbol', '')) > 6]
    
    print(f"  Stock orders: {len(stock_orders)}")
    print(f"  Option orders: {len(option_orders)}")
    
    if stock_orders:
        print(f"\n⚠️  WARNING: Found {len(stock_orders)} STOCK orders (system should only trade OPTIONS)")
        for order in stock_orders:
            print(f"    - {order.get('symbol')}: {order.get('side')} {order.get('qty')}")
    
    # Check positions for stocks vs options
    stock_positions = [p for p in positions if not (p.get('asset_class') == 'option' or 'C' in p.get('symbol', '') or 'P' in p.get('symbol', '') or len(p.get('symbol', '')) > 6)]
    option_positions = [p for p in positions if p.get('asset_class') == 'option' or 'C' in p.get('symbol', '') or 'P' in p.get('symbol', '') or len(p.get('symbol', '')) > 6]
    
    print(f"\n  Stock positions: {len(stock_positions)}")
    print(f"  Option positions: {len(option_positions)}")
    
    if stock_positions:
        print(f"\n⚠️  WARNING: Found {len(stock_positions)} STOCK positions (system should only trade OPTIONS)")
        for pos in stock_positions:
            print(f"    - {pos.get('symbol')}: {pos.get('qty')} @ ${pos.get('avg_entry_price', 0):.2f}")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == '__main__':
    analyze_today()

