"""
Trade Loader Utility
Loads trades from both backtest results and live Alpaca orders
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def load_backtest_trades() -> List[Dict]:
    """Load trades from backtest result JSON files"""
    trades = []
    logs_dir = Path('logs')
    
    if not logs_dir.exists():
        return trades
    
    # Find all backtest result files
    backtest_files = list(logs_dir.glob('backtest_results_*.json'))
    
    # Sort by modification time (newest first)
    backtest_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    for file_path in backtest_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if 'trades' in data:
                    for trade in data['trades']:
                        # Add source info
                        trade['source'] = 'Backtest'
                        trade['backtest_file'] = file_path.name
                        trades.append(trade)
        except Exception as e:
            logger.warning(f"Error loading {file_path.name}: {e}")
            continue
    
    return trades

def load_live_trades_from_alpaca() -> List[Dict]:
    """Load trades from live Alpaca orders"""
    trades = []
    
    try:
        from config import Config
        from alpaca_client import AlpacaClient
        
        # Validate config
        if not Config.ALPACA_API_KEY or not Config.ALPACA_SECRET_KEY:
            logger.debug("Alpaca credentials not configured")
            return trades
        
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        # Get all filled orders
        orders = client.get_orders(status='all', limit=200)
        
        # Group orders by symbol to match buy/sell pairs
        order_pairs = {}
        
        for order in orders:
            if order['status'] != 'filled' or not order.get('filled_avg_price'):
                continue
            
            symbol = order['symbol']
            side = order['side']
            filled_qty = order.get('filled_qty', order['qty'])
            filled_price = order['filled_avg_price']
            
            # Get order timestamp (approximate from order ID or use current time)
            # Alpaca order IDs contain timestamp info, but we'll use a simpler approach
            order_time = datetime.now()  # Fallback
            
            if symbol not in order_pairs:
                order_pairs[symbol] = {'buys': [], 'sells': []}
            
            order_info = {
                'time': order_time,
                'qty': filled_qty,
                'price': filled_price,
                'order_id': order.get('id', '')
            }
            
            if side == 'buy':
                order_pairs[symbol]['buys'].append(order_info)
            else:
                order_pairs[symbol]['sells'].append(order_info)
        
        # Match buy/sell pairs to create trades
        for symbol, pairs in order_pairs.items():
            buys = sorted(pairs['buys'], key=lambda x: x['time'])
            sells = sorted(pairs['sells'], key=lambda x: x['time'])
            
            # Simple matching: pair earliest buy with earliest sell
            buy_idx = 0
            sell_idx = 0
            
            while buy_idx < len(buys) and sell_idx < len(sells):
                buy = buys[buy_idx]
                sell = sells[sell_idx]
                
                # Create trade entry
                entry_price = buy['price']
                exit_price = sell['price']
                qty = min(buy['qty'], sell['qty'])
                
                pnl = (exit_price - entry_price) * qty
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                
                trade = {
                    'symbol': symbol,
                    'entry_time': buy['time'].isoformat() if hasattr(buy['time'], 'isoformat') else str(buy['time']),
                    'exit_time': sell['time'].isoformat() if hasattr(sell['time'], 'isoformat') else str(sell['time']),
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'qty': qty,
                    'side': 'long',
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reason': 'live_trade',
                    'agent': 'Live Trading',
                    'source': 'Live Trading',
                    'order_id': f"{buy['order_id']}/{sell['order_id']}"
                }
                
                trades.append(trade)
                
                # Reduce quantities
                buy['qty'] -= qty
                sell['qty'] -= qty
                
                if buy['qty'] <= 0:
                    buy_idx += 1
                if sell['qty'] <= 0:
                    sell_idx += 1
            
            # Handle unmatched positions (still open)
            for buy in buys[buy_idx:]:
                if buy['qty'] > 0:
                    # Open position
                    current_price = entry_price  # Would need to fetch from positions API
                    trade = {
                        'symbol': symbol,
                        'entry_time': buy['time'].isoformat() if hasattr(buy['time'], 'isoformat') else str(buy['time']),
                        'exit_time': None,
                        'entry_price': buy['price'],
                        'exit_price': None,
                        'qty': buy['qty'],
                        'side': 'long',
                        'pnl': None,  # Unrealized
                        'pnl_pct': None,
                        'reason': 'open_position',
                        'agent': 'Live Trading',
                        'source': 'Live Trading',
                        'order_id': buy['order_id']
                    }
                    trades.append(trade)
        
            # Also get current positions for open trades
            positions = client.get_positions()
            for pos in positions:
                # Check if we already have this as an open trade
                existing = [t for t in trades if t['symbol'] == pos['symbol'] and t.get('exit_time') is None]
                if not existing:
                    trade = {
                        'symbol': pos['symbol'],
                        'entry_time': datetime.now().isoformat(),  # Approximate
                        'exit_time': None,
                        'entry_price': pos.get('avg_entry_price', 0),
                        'exit_price': pos.get('current_price', 0),
                        'qty': abs(pos.get('qty', 0)),
                        'side': pos.get('side', 'long'),
                        'pnl': pos.get('unrealized_pl', 0),
                        'pnl_pct': pos.get('unrealized_plpc', 0) * 100 if pos.get('unrealized_plpc') else None,
                        'reason': 'open_position',
                        'agent': 'Live Trading',
                        'source': 'Live Trading',
                        'order_id': 'current_position'
                    }
                    trades.append(trade)
        
    except ImportError as e:
        logger.debug(f"Could not import Alpaca modules: {e}")
        # Alpaca modules not available, return empty
    except Exception as e:
        logger.error(f"Error loading live trades from Alpaca: {e}")
        # Don't fail completely, just return empty list
    
    return trades

def load_all_trades() -> List[Dict]:
    """Load trades from both backtest results and live Alpaca orders"""
    all_trades = []
    
    # Load backtest trades
    backtest_trades = load_backtest_trades()
    all_trades.extend(backtest_trades)
    
    # Load live trades
    live_trades = load_live_trades_from_alpaca()
    all_trades.extend(live_trades)
    
    return all_trades

