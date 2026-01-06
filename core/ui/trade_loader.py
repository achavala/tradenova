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
    """Load trades from live Alpaca orders and positions"""
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
        
        # First, get all current positions with real P&L
        positions = client.get_positions()
        position_symbols = set()
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            position_symbols.add(symbol)
            
            qty = abs(float(pos.get('qty', 0)))
            entry_price = float(pos.get('avg_entry_price', 0))
            current_price = float(pos.get('current_price', 0))
            unrealized_pl = float(pos.get('unrealized_pl', 0))
            unrealized_plpc = float(pos.get('unrealized_plpc', 0)) * 100  # Convert to %
            cost_basis = float(pos.get('cost_basis', 0))
            market_value = float(pos.get('market_value', 0))
            
            # Determine if this is an option
            is_option = len(symbol) > 10  # Options symbols are longer
            
            # Extract underlying for options
            underlying = symbol[:4].rstrip('0123456789') if is_option else symbol
            
            trade = {
                'symbol': symbol,
                'underlying': underlying,
                'entry_time': datetime.now().isoformat(),  # Will be updated from orders
                'exit_time': None,  # Still open
                'entry_price': entry_price,
                'exit_price': current_price,  # Current price (unrealized)
                'qty': qty,
                'side': pos.get('side', 'long'),
                'pnl': unrealized_pl,
                'pnl_pct': unrealized_plpc,
                'cost_basis': cost_basis,
                'market_value': market_value,
                'reason': 'open_position',
                'status': 'OPEN',
                'agent': 'Live Trading',
                'source': 'Live Trading',
                'is_option': is_option
            }
            trades.append(trade)
        
        # Next, get filled orders to find entry times and closed trades
        orders = client.get_orders(status='all', limit=200)
        
        # Track orders by symbol
        symbol_orders = {}
        for order in orders:
            if order.get('status') != 'filled':
                continue
            
            symbol = order.get('symbol', '')
            if symbol not in symbol_orders:
                symbol_orders[symbol] = []
            
            symbol_orders[symbol].append({
                'id': order.get('id', ''),
                'side': order.get('side', ''),
                'qty': float(order.get('filled_qty', order.get('qty', 0))),
                'price': float(order.get('filled_avg_price', 0)),
                'created_at': order.get('created_at', datetime.now().isoformat()),
                'filled_at': order.get('filled_at', order.get('created_at', datetime.now().isoformat()))
            })
        
        # Update entry times for open positions
        for trade in trades:
            symbol = trade['symbol']
            if symbol in symbol_orders:
                # Find the earliest buy order for this symbol
                buy_orders = [o for o in symbol_orders[symbol] if o['side'] == 'buy']
                if buy_orders:
                    buy_orders.sort(key=lambda x: x['filled_at'])
                    trade['entry_time'] = buy_orders[0]['filled_at']
        
        # Find closed trades (matched buy/sell pairs for symbols not in current positions)
        for symbol, orders_list in symbol_orders.items():
            if symbol in position_symbols:
                continue  # Skip if we still have open position
            
            buys = sorted([o for o in orders_list if o['side'] == 'buy'], key=lambda x: x['filled_at'])
            sells = sorted([o for o in orders_list if o['side'] == 'sell'], key=lambda x: x['filled_at'])
            
            # Match buys with sells
            buy_idx = 0
            sell_idx = 0
            
            while buy_idx < len(buys) and sell_idx < len(sells):
                buy = buys[buy_idx]
                sell = sells[sell_idx]
                
                qty = min(buy['qty'], sell['qty'])
                entry_price = buy['price']
                exit_price = sell['price']
                
                pnl = (exit_price - entry_price) * qty * (100 if len(symbol) > 10 else 1)  # Options = 100 shares
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                
                is_option = len(symbol) > 10
                underlying = symbol[:4].rstrip('0123456789') if is_option else symbol
                
                closed_trade = {
                    'symbol': symbol,
                    'underlying': underlying,
                    'entry_time': buy['filled_at'],
                    'exit_time': sell['filled_at'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'qty': qty,
                    'side': 'long',
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reason': 'closed_trade',
                    'status': 'CLOSED',
                    'agent': 'Live Trading',
                    'source': 'Live Trading',
                    'is_option': is_option,
                    'order_id': f"{buy['id']}/{sell['id']}"
                }
                trades.append(closed_trade)
                
                buy['qty'] -= qty
                sell['qty'] -= qty
                
                if buy['qty'] <= 0:
                    buy_idx += 1
                if sell['qty'] <= 0:
                    sell_idx += 1
        
    except ImportError as e:
        logger.debug(f"Could not import Alpaca modules: {e}")
    except Exception as e:
        logger.error(f"Error loading live trades from Alpaca: {e}")
        import traceback
        traceback.print_exc()
    
    return trades

def load_all_trades(include_backtest: bool = False) -> List[Dict]:
    """Load trades from both backtest results and live Alpaca orders
    
    Args:
        include_backtest: If True, include backtest trades. Default False to show only live trades.
    """
    all_trades = []
    
    # Load backtest trades (only if requested)
    if include_backtest:
        backtest_trades = load_backtest_trades()
        all_trades.extend(backtest_trades)
    
    # Load live trades (always included)
    live_trades = load_live_trades_from_alpaca()
    all_trades.extend(live_trades)
    
    return all_trades
