#!/usr/bin/env python3
"""
Analyze Executed Trades from Logs and Alpaca
Extract all trade details: entry, exit, P&L
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import re
from datetime import datetime
from typing import List, Dict, Optional
from alpaca_client import AlpacaClient
from config import Config
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def parse_logs_for_trades() -> List[Dict]:
    """Parse logs to extract trade information"""
    log_file = Path("logs/tradenova_daily.log")
    if not log_file.exists():
        return []
    
    trades = []
    current_trade = None
    
    with open(log_file, 'r') as f:
        for line in f:
            # Match trade execution
            if "EXECUTING TRADE" in line or "OPTIONS TRADE EXECUTED" in line:
                # Extract timestamp
                ts_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if ts_match:
                    timestamp = ts_match.group(1)
                    
                    # Extract symbol
                    symbol_match = re.search(r'(\b[A-Z]{2,5}\b)', line)
                    symbol = symbol_match.group(1) if symbol_match else "UNKNOWN"
                    
                    current_trade = {
                        'entry_time': timestamp,
                        'symbol': symbol,
                        'option_type': None,
                        'option_symbol': None,
                        'direction': None,
                        'qty': None,
                        'entry_price': None,
                        'strike': None,
                        'expiration': None,
                        'dte': None,
                        'confidence': None,
                        'agent': None
                    }
            
            # Extract option type
            if current_trade:
                if "CALL" in line:
                    current_trade['option_type'] = 'CALL'
                elif "PUT" in line:
                    current_trade['option_type'] = 'PUT'
                
                # Extract option symbol
                if "option symbol" in line.lower() or "Executing OPTIONS trade" in line:
                    opt_match = re.search(r'([A-Z]{1,5}\d{6}[CP]\d{8})', line)
                    if opt_match:
                        current_trade['option_symbol'] = opt_match.group(1)
                
                # Extract price
                price_match = re.search(r'\$(\d+\.?\d*)', line)
                if price_match and not current_trade['entry_price']:
                    try:
                        current_trade['entry_price'] = float(price_match.group(1))
                    except:
                        pass
                
                # Extract contracts
                qty_match = re.search(r'(\d+)\s*contracts?', line, re.IGNORECASE)
                if qty_match:
                    current_trade['qty'] = int(qty_match.group(1))
                
                # Extract direction
                if "LONG" in line:
                    current_trade['direction'] = 'LONG'
                elif "SHORT" in line:
                    current_trade['direction'] = 'SHORT'
                
                # Extract confidence
                conf_match = re.search(r'(\d+\.?\d*)%', line)
                if conf_match:
                    try:
                        current_trade['confidence'] = float(conf_match.group(1)) / 100
                    except:
                        pass
                
                # If we have enough info, save trade
                if current_trade.get('entry_time') and current_trade.get('symbol'):
                    # Check if this is a complete trade entry
                    if "TRADE EXECUTED" in line or "filled" in line.lower():
                        trades.append(current_trade.copy())
                        current_trade = None
    
    return trades

def get_alpaca_positions() -> List[Dict]:
    """Get current positions from Alpaca"""
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        positions = client.get_positions()
        return positions
    except Exception as e:
        print(f"Error getting Alpaca positions: {e}")
        return []

def get_alpaca_orders() -> List[Dict]:
    """Get order history from Alpaca"""
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        orders = client.api.list_orders(status='all', limit=100)
        
        order_list = []
        for order in orders:
            order_list.append({
                'id': order.id,
                'symbol': order.symbol,
                'side': order.side,
                'qty': float(order.qty),
                'type': order.type,
                'status': order.status,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'created_at': order.created_at.isoformat() if hasattr(order.created_at, 'isoformat') else str(order.created_at),
                'updated_at': order.updated_at.isoformat() if hasattr(order.updated_at, 'isoformat') else str(order.updated_at)
            })
        
        return order_list
    except Exception as e:
        print(f"Error getting Alpaca orders: {e}")
        return []

def analyze_trades():
    """Main analysis function"""
    print("="*60)
    print("EXECUTED TRADES ANALYSIS")
    print("="*60)
    print()
    
    # Get trades from logs
    log_trades = parse_logs_for_trades()
    print(f"📊 Trades found in logs: {len(log_trades)}")
    
    # Get positions from Alpaca
    positions = get_alpaca_positions()
    print(f"📊 Current positions in Alpaca: {len(positions)}")
    
    # Get orders from Alpaca
    orders = get_alpaca_orders()
    print(f"📊 Total orders in Alpaca: {len(orders)}")
    print()
    
    # Combine data
    all_trades = []
    
    # Process orders (most reliable source)
    for order in orders:
        if order['status'] in ['filled', 'partially_filled'] and order['filled_qty'] > 0:
            # Determine if it's an option (longer symbol)
            is_option = len(order['symbol']) > 10
            
            trade = {
                'entry_time': order['created_at'],
                'symbol': order['symbol'],
                'side': order['side'],
                'qty': order['filled_qty'],
                'entry_price': order['filled_avg_price'],
                'status': order['status'],
                'is_option': is_option,
                'exit_time': None,
                'exit_price': None,
                'pnl': None,
                'current_price': None
            }
            
            # If position still open, get current price
            matching_pos = next((p for p in positions if p.get('symbol') == order['symbol']), None)
            if matching_pos:
                trade['current_price'] = matching_pos.get('current_price', 0)
                trade['unrealized_pl'] = matching_pos.get('unrealized_pl', 0)
                trade['status'] = 'OPEN'
            else:
                trade['status'] = 'CLOSED'
            
            all_trades.append(trade)
    
    # Create DataFrame
    if all_trades:
        df = pd.DataFrame(all_trades)
        
        # Format for display
        print("="*60)
        print("EXECUTED TRADES TABLE")
        print("="*60)
        print()
        
        # Sort by entry time
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df = df.sort_values('entry_time')
        
        # Display table
        print(f"{'Entry Time':<20} {'Symbol':<15} {'Side':<6} {'Qty':<8} {'Entry Price':<12} {'Status':<10} {'Current Price':<14} {'P&L':<12}")
        print("-"*120)
        
        for _, trade in df.iterrows():
            entry_time = trade['entry_time'].strftime('%Y-%m-%d %H:%M') if pd.notna(trade['entry_time']) else 'N/A'
            symbol = str(trade['symbol'])[:14]
            side = str(trade['side'])[:5]
            qty = f"{trade['qty']:.0f}" if pd.notna(trade['qty']) else 'N/A'
            entry_price = f"${trade['entry_price']:.2f}" if pd.notna(trade['entry_price']) else 'N/A'
            status = str(trade['status'])[:9]
            current_price = f"${trade['current_price']:.2f}" if pd.notna(trade['current_price']) and trade['current_price'] > 0 else 'N/A'
            
            pnl = trade.get('unrealized_pl', 0)
            if pd.notna(pnl) and pnl != 0:
                pnl_str = f"${pnl:.2f}"
            else:
                pnl_str = 'N/A'
            
            print(f"{entry_time:<20} {symbol:<15} {side:<6} {qty:<8} {entry_price:<12} {status:<10} {current_price:<14} {pnl_str:<12}")
        
        print()
        print("="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total Trades: {len(df)}")
        print(f"Open Positions: {len(df[df['status'] == 'OPEN'])}")
        print(f"Closed Positions: {len(df[df['status'] == 'CLOSED'])}")
        
        open_trades = df[df['status'] == 'OPEN']
        if len(open_trades) > 0:
            total_unrealized = open_trades['unrealized_pl'].sum()
            print(f"Total Unrealized P&L: ${total_unrealized:.2f}")
        
        # Save to CSV
        csv_file = Path("backtest_results") / f"executed_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_file.parent.mkdir(exist_ok=True)
        df.to_csv(csv_file, index=False)
        print(f"\n📄 Saved to: {csv_file}")
        
    else:
        print("❌ No executed trades found")
        print("\nPossible reasons:")
        print("  1. System hasn't executed any trades yet")
        print("  2. Market was closed during test period")
        print("  3. All signals were rejected by risk manager")
        print("  4. Position size too small for options")
        print("\nCheck logs for details:")
        print("  tail -f logs/tradenova_daily.log | grep -E 'EXECUTING|BLOCKED|rejected'")

if __name__ == '__main__':
    analyze_trades()




