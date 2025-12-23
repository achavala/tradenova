#!/usr/bin/env python3
"""
Get Detailed Trade Table with Entry/Exit Times and P&L
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from alpaca_client import AlpacaClient
from config import Config
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def get_all_trade_details():
    """Get all trade details from Alpaca"""
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    print("="*100)
    print("EXECUTED TRADES DETAILED TABLE")
    print("="*100)
    print()
    
    # Get all orders
    orders = client.api.list_orders(status='all', limit=200)
    
    # Get current positions
    positions = client.get_positions()
    position_dict = {p['symbol']: p for p in positions}
    
    # Process orders into trades
    trades = []
    for order in orders:
        filled_qty = float(order.filled_qty) if order.filled_qty else 0
        if order.status in ['filled', 'partially_filled'] and filled_qty > 0:
            # Determine if option (longer symbol)
            is_option = len(order.symbol) > 10
            
            # Get entry info
            entry_time = order.created_at
            if hasattr(entry_time, 'isoformat'):
                entry_time_str = entry_time.isoformat()
            else:
                entry_time_str = str(entry_time)
            
            # Check if position is still open
            pos = position_dict.get(order.symbol)
            
            trade = {
                'Entry Date': entry_time.strftime('%Y-%m-%d') if hasattr(entry_time, 'strftime') else str(entry_time).split()[0],
                'Entry Time': entry_time.strftime('%H:%M:%S') if hasattr(entry_time, 'strftime') else str(entry_time).split()[1] if len(str(entry_time).split()) > 1 else 'N/A',
                'Symbol': order.symbol,
                'Type': 'OPTION' if is_option else 'STOCK',
                'Side': order.side.upper(),
                'Quantity': filled_qty,
                'Entry Price': float(order.filled_avg_price) if order.filled_avg_price else 0,
                'Status': 'OPEN' if pos else 'CLOSED',
                'Exit Date': None,
                'Exit Time': None,
                'Exit Price': None,
                'Current Price': pos['current_price'] if pos else None,
                'Unrealized P&L': pos['unrealized_pl'] if pos else None,
                'Realized P&L': None,  # Will calculate for closed positions
                'Total P&L': None,
                'Days Held': None
            }
            
            # For closed positions, try to find exit order
            if not pos:
                # Look for opposite side order
                exit_orders = [o for o in orders 
                              if o.symbol == order.symbol 
                              and o.side != order.side 
                              and o.status in ['filled', 'partially_filled']
                              and o.created_at > entry_time]
                
                if exit_orders:
                    exit_order = exit_orders[0]  # Take first exit
                    exit_time = exit_order.created_at
                    trade['Exit Date'] = exit_time.strftime('%Y-%m-%d') if hasattr(exit_time, 'strftime') else str(exit_time).split()[0]
                    trade['Exit Time'] = exit_time.strftime('%H:%M:%S') if hasattr(exit_time, 'strftime') else str(exit_time).split()[1] if len(str(exit_time).split()) > 1 else 'N/A'
                    trade['Exit Price'] = float(exit_order.filled_avg_price) if exit_order.filled_avg_price else None
                    
                    # Calculate realized P&L
                    if trade['Exit Price']:
                        if order.side == 'buy':
                            realized_pnl = (trade['Exit Price'] - trade['Entry Price']) * trade['Quantity']
                        else:  # sell
                            realized_pnl = (trade['Entry Price'] - trade['Exit Price']) * trade['Quantity']
                        trade['Realized P&L'] = realized_pnl
                        trade['Total P&L'] = realized_pnl
                    
                    # Calculate days held
                    if hasattr(entry_time, 'date') and hasattr(exit_time, 'date'):
                        days_held = (exit_time.date() - entry_time.date()).days
                        trade['Days Held'] = days_held
                    elif hasattr(entry_time, 'date'):
                        days_held = (datetime.now().date() - entry_time.date()).days
                        trade['Days Held'] = days_held
            
            # For open positions, calculate unrealized P&L
            if pos and trade['Current Price']:
                if order.side == 'buy':
                    unrealized_pnl = (trade['Current Price'] - trade['Entry Price']) * trade['Quantity']
                else:  # sell (short)
                    unrealized_pnl = (trade['Entry Price'] - trade['Current Price']) * trade['Quantity']
                
                trade['Unrealized P&L'] = unrealized_pnl
                trade['Total P&L'] = unrealized_pnl
                
                # Calculate days held
                if hasattr(entry_time, 'date'):
                    days_held = (datetime.now().date() - entry_time.date()).days
                    trade['Days Held'] = days_held
            
            trades.append(trade)
    
    # Create DataFrame
    if trades:
        df = pd.DataFrame(trades)
        df = df.sort_values(['Entry Date', 'Entry Time'])
        
        # Display table
        print(f"{'Entry Date':<12} {'Entry Time':<10} {'Symbol':<20} {'Type':<8} {'Side':<6} {'Qty':<8} {'Entry $':<10} {'Status':<8} {'Exit Date':<12} {'Exit Time':<10} {'Exit $':<10} {'Days':<6} {'P&L':<12}")
        print("-"*140)
        
        for _, trade in df.iterrows():
            entry_date = str(trade['Entry Date'])[:12]
            entry_time = str(trade['Entry Time'])[:10]
            symbol = str(trade['Symbol'])[:19]
            trade_type = str(trade['Type'])[:7]
            side = str(trade['Side'])[:5]
            qty = f"{trade['Quantity']:.0f}" if pd.notna(trade['Quantity']) else 'N/A'
            entry_price = f"${trade['Entry Price']:.2f}" if pd.notna(trade['Entry Price']) else 'N/A'
            status = str(trade['Status'])[:7]
            exit_date = str(trade['Exit Date'])[:12] if pd.notna(trade['Exit Date']) else 'N/A'
            exit_time = str(trade['Exit Time'])[:10] if pd.notna(trade['Exit Time']) else 'N/A'
            exit_price = f"${trade['Exit Price']:.2f}" if pd.notna(trade['Exit Price']) and trade['Exit Price'] > 0 else 'N/A'
            days = f"{trade['Days Held']}" if pd.notna(trade['Days Held']) else 'N/A'
            
            # P&L
            if pd.notna(trade['Total P&L']):
                pnl = trade['Total P&L']
                pnl_str = f"${pnl:+.2f}" if pnl != 0 else "$0.00"
            else:
                pnl_str = 'N/A'
            
            print(f"{entry_date:<12} {entry_time:<10} {symbol:<20} {trade_type:<8} {side:<6} {qty:<8} {entry_price:<10} {status:<8} {exit_date:<12} {exit_time:<10} {exit_price:<10} {days:<6} {pnl_str:<12}")
        
        print()
        print("="*100)
        print("SUMMARY")
        print("="*100)
        
        total_trades = len(df)
        open_trades = len(df[df['Status'] == 'OPEN'])
        closed_trades = len(df[df['Status'] == 'CLOSED'])
        
        total_realized = df[df['Realized P&L'].notna()]['Realized P&L'].sum()
        total_unrealized = df[df['Unrealized P&L'].notna()]['Unrealized P&L'].sum()
        total_pnl = (df[df['Total P&L'].notna()]['Total P&L'].sum())
        
        print(f"Total Trades: {total_trades}")
        print(f"  - Open: {open_trades}")
        print(f"  - Closed: {closed_trades}")
        print(f"  - Options: {len(df[df['Type'] == 'OPTION'])}")
        print(f"  - Stocks: {len(df[df['Type'] == 'STOCK'])}")
        print()
        print(f"P&L Summary:")
        print(f"  - Realized P&L: ${total_realized:.2f}" if pd.notna(total_realized) else "  - Realized P&L: N/A")
        print(f"  - Unrealized P&L: ${total_unrealized:.2f}" if pd.notna(total_unrealized) else "  - Unrealized P&L: N/A")
        print(f"  - Total P&L: ${total_pnl:.2f}" if pd.notna(total_pnl) else "  - Total P&L: N/A")
        print()
        
        # Save to CSV
        csv_file = Path("backtest_results") / f"trade_details_table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_file.parent.mkdir(exist_ok=True)
        df.to_csv(csv_file, index=False)
        print(f"📄 Detailed table saved to: {csv_file}")
        
        # Also create formatted markdown table
        md_file = Path("backtest_results") / f"trade_details_table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(md_file, 'w') as f:
            f.write("# Executed Trades Detailed Table\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- **Total Trades:** {total_trades}\n")
            f.write(f"- **Open Positions:** {open_trades}\n")
            f.write(f"- **Closed Positions:** {closed_trades}\n")
            f.write(f"- **Total P&L:** ${total_pnl:.2f}\n\n")
            f.write("## Trade Details\n\n")
            f.write("| Entry Date | Entry Time | Symbol | Type | Side | Qty | Entry Price | Status | Exit Date | Exit Time | Exit Price | Days | P&L |\n")
            f.write("|------------|------------|--------|------|------|-----|-------------|--------|------------|-----------|------------|------|-----|\n")
            
            for _, trade in df.iterrows():
                entry_date = str(trade['Entry Date'])[:12]
                entry_time = str(trade['Entry Time'])[:10]
                symbol = str(trade['Symbol'])
                trade_type = str(trade['Type'])
                side = str(trade['Side'])
                qty = f"{trade['Quantity']:.0f}" if pd.notna(trade['Quantity']) else 'N/A'
                entry_price = f"${trade['Entry Price']:.2f}" if pd.notna(trade['Entry Price']) else 'N/A'
                status = str(trade['Status'])
                exit_date = str(trade['Exit Date']) if pd.notna(trade['Exit Date']) else 'N/A'
                exit_time = str(trade['Exit Time']) if pd.notna(trade['Exit Time']) else 'N/A'
                exit_price = f"${trade['Exit Price']:.2f}" if pd.notna(trade['Exit Price']) and trade['Exit Price'] > 0 else 'N/A'
                days = f"{trade['Days Held']}" if pd.notna(trade['Days Held']) else 'N/A'
                pnl = f"${trade['Total P&L']:+.2f}" if pd.notna(trade['Total P&L']) else 'N/A'
                
                f.write(f"| {entry_date} | {entry_time} | {symbol} | {trade_type} | {side} | {qty} | {entry_price} | {status} | {exit_date} | {exit_time} | {exit_price} | {days} | {pnl} |\n")
        
        print(f"📄 Markdown table saved to: {md_file}")
        
    else:
        print("❌ No trades found")

if __name__ == '__main__':
    get_all_trade_details()

