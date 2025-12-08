"""
TradeNova - Advanced Options Trading Agent
Main agent class that orchestrates all trading activities
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

from config import Config
from alpaca_client import AlpacaClient
from position import Position
from strategy import SwingScalpStrategy

logger = logging.getLogger(__name__)

class TradeNova:
    """
    TradeNova Trading Agent
    
    Features:
    - Maximum 10 active trades
    - Uses 50% of previous day ending balance
    - Advanced profit target scaling (TP1-TP5)
    - Trailing stop after TP4
    - 15% stop loss always
    - Swing and scalp strategies
    """
    
    def __init__(self):
        """Initialize TradeNova agent"""
        # Validate configuration
        Config.validate()
        
        # Initialize clients
        self.client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        self.strategy = SwingScalpStrategy(self.client)
        
        # Position tracking
        self.positions: Dict[str, Position] = {}
        self.max_active_trades = Config.MAX_ACTIVE_TRADES
        
        # Balance tracking
        self.daily_balance_file = Path('daily_balance.json')
        self.previous_day_balance = self._load_previous_balance()
        self.current_balance = None
        
        # Configuration
        self.position_size_pct = Config.POSITION_SIZE_PCT
        self.stop_loss_pct = Config.STOP_LOSS_PCT
        
        # Profit target configuration
        self.profit_target_config = {
            'stop_loss_pct': Config.STOP_LOSS_PCT,
            'tp1_pct': Config.TP1_PCT,
            'tp1_exit_pct': Config.TP1_EXIT_PCT,
            'tp2_pct': Config.TP2_PCT,
            'tp2_exit_pct': Config.TP2_EXIT_PCT,
            'tp3_pct': Config.TP3_PCT,
            'tp3_exit_pct': Config.TP3_EXIT_PCT,
            'tp4_pct': Config.TP4_PCT,
            'tp4_exit_pct': Config.TP4_EXIT_PCT,
            'tp5_pct': Config.TP5_PCT,
            'tp5_exit_pct': Config.TP5_EXIT_PCT,
            'trailing_stop_activation_pct': Config.TRAILING_STOP_ACTIVATION_PCT,
            'trailing_stop_min_profit_pct': Config.TRAILING_STOP_MIN_PROFIT_PCT
        }
        
        logger.info("TradeNova agent initialized")
        logger.info(f"Previous day balance: ${self.previous_day_balance:,.2f}")
        logger.info(f"Max active trades: {self.max_active_trades}")
    
    def _load_previous_balance(self) -> float:
        """Load previous day's ending balance"""
        if self.daily_balance_file.exists():
            try:
                with open(self.daily_balance_file, 'r') as f:
                    data = json.load(f)
                    return float(data.get('balance', Config.INITIAL_BALANCE))
            except Exception as e:
                logger.warning(f"Error loading previous balance: {e}")
        
        return Config.INITIAL_BALANCE
    
    def _save_daily_balance(self, balance: float):
        """Save daily ending balance"""
        try:
            data = {
                'balance': balance,
                'date': datetime.now().isoformat()
            }
            with open(self.daily_balance_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving daily balance: {e}")
    
    def get_account_status(self) -> Dict:
        """Get current account status"""
        account = self.client.get_account()
        self.current_balance = account['equity']
        return account
    
    def get_active_positions_count(self) -> int:
        """Get count of active positions"""
        return len([p for p in self.positions.values() if not p.is_closed()])
    
    def can_open_new_position(self) -> bool:
        """Check if we can open a new position"""
        return self.get_active_positions_count() < self.max_active_trades
    
    def calculate_position_size(self, price: float) -> float:
        """
        Calculate position size using 50% of previous day balance
        
        Args:
            price: Entry price
            
        Returns:
            Quantity to trade
        """
        available_capital = self.previous_day_balance * self.position_size_pct
        total_capital = self.previous_day_balance
        
        # Distribute across max positions
        capital_per_position = total_capital / self.max_active_trades
        
        # Use the smaller of: 50% of balance / max positions, or available capital
        position_capital = min(capital_per_position, available_capital)
        
        # Calculate quantity
        qty = position_capital / price
        
        # Round down to whole shares (for stocks) or appropriate precision for options
        qty = int(qty) if qty >= 1 else round(qty, 2)
        
        logger.info(f"Position size calculation: ${position_capital:,.2f} / ${price:.2f} = {qty}")
        
        return qty
    
    def sync_positions(self):
        """Sync positions with Alpaca account"""
        try:
            alpaca_positions = self.client.get_positions()
            alpaca_symbols = {pos['symbol'] for pos in alpaca_positions}
            
            # Update existing positions
            for symbol, position in list(self.positions.items()):
                if symbol in alpaca_symbols:
                    alpaca_pos = next(p for p in alpaca_positions if p['symbol'] == symbol)
                    # Update position with current price
                    current_price = alpaca_pos['current_price']
                    position.update_price(current_price)
                    position.update_trailing_stop(current_price)
                elif position.is_closed():
                    # Position closed, remove from tracking
                    del self.positions[symbol]
            
            # Add new positions from Alpaca
            for alpaca_pos in alpaca_positions:
                symbol = alpaca_pos['symbol']
                if symbol not in self.positions:
                    # Create new position object
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        qty=alpaca_pos['qty'],
                        entry_price=alpaca_pos['avg_entry_price'],
                        side='long' if alpaca_pos['qty'] > 0 else 'short',
                        config=self.profit_target_config
                    )
                    logger.info(f"Synced new position: {symbol}")
        
        except Exception as e:
            logger.error(f"Error syncing positions: {e}")
    
    def monitor_positions(self):
        """Monitor all positions for exits"""
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            if position.is_closed():
                continue
            
            # Get current price
            current_price = self.client.get_latest_price(symbol)
            if current_price is None:
                logger.warning(f"Could not get price for {symbol}")
                continue
            
            # Update position
            action = position.update_price(current_price)
            position.update_trailing_stop(current_price)
            
            # Check for exit actions
            if action['action'] != 'hold':
                positions_to_close.append({
                    'symbol': symbol,
                    'position': position,
                    'action': action,
                    'current_price': current_price
                })
        
        # Execute exits
        for exit_info in positions_to_close:
            self._execute_exit(exit_info)
    
    def _execute_exit(self, exit_info: Dict):
        """Execute position exit"""
        symbol = exit_info['symbol']
        position = exit_info['position']
        action = exit_info['action']
        current_price = exit_info['current_price']
        
        qty = action['qty']
        
        try:
            # Place sell order
            order = self.client.place_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                order_type='market'
            )
            
            if order:
                logger.info(f"Exit executed: {symbol} - {action['reason']}")
                logger.info(f"  Quantity: {qty}, Price: ${current_price:.2f}")
                
                # Update position
                if action['action'] in ['full_exit', 'stop_loss', 'trailing_stop']:
                    position.current_qty = 0
            else:
                logger.error(f"Failed to execute exit for {symbol}")
        
        except Exception as e:
            logger.error(f"Error executing exit for {symbol}: {e}")
    
    def scan_and_trade(self):
        """Scan for trading opportunities and execute trades"""
        if not self.can_open_new_position():
            logger.info(f"Max positions reached ({self.max_active_trades})")
            return
        
        if not self.client.is_market_open():
            logger.info("Market is closed")
            return
        
        # Scan all tickers
        signals = []
        for ticker in Config.TICKERS:
            # Skip if we already have a position
            if ticker in self.positions and not self.positions[ticker].is_closed():
                continue
            
            # Get signal
            signal = self.strategy.get_signal(ticker)
            if signal and signal['action'] == 'buy' and signal['confidence'] > 0.6:
                signals.append(signal)
        
        # Sort by confidence
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Execute top signals
        for signal in signals:
            if not self.can_open_new_position():
                break
            
            self._execute_entry(signal)
    
    def _execute_entry(self, signal: Dict):
        """Execute trade entry"""
        symbol = signal['symbol']
        current_price = signal['current_price']
        
        # Calculate position size
        qty = self.calculate_position_size(current_price)
        
        if qty < 0.01:  # Minimum position size
            logger.warning(f"Position size too small for {symbol}: {qty}")
            return
        
        try:
            # Place buy order
            order = self.client.place_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                order_type='market'
            )
            
            if order and order.get('status') == 'filled':
                filled_price = order.get('filled_avg_price', current_price)
                filled_qty = order.get('filled_qty', qty)
                
                # Create position object
                self.positions[symbol] = Position(
                    symbol=symbol,
                    qty=filled_qty,
                    entry_price=filled_price,
                    side='long',
                    config=self.profit_target_config
                )
                
                logger.info(f"Entry executed: {symbol}")
                logger.info(f"  Quantity: {filled_qty}, Entry: ${filled_price:.2f}")
                logger.info(f"  Confidence: {signal['confidence']:.2%}")
                logger.info(f"  Reasons: {', '.join(signal['reasons'])}")
            else:
                logger.warning(f"Order not filled for {symbol}: {order}")
        
        except Exception as e:
            logger.error(f"Error executing entry for {symbol}: {e}")
    
    def run_daily_close(self):
        """Run at end of trading day"""
        # Update balance
        account = self.get_account_status()
        ending_balance = account['equity']
        
        # Save for next day
        self._save_daily_balance(ending_balance)
        self.previous_day_balance = ending_balance
        
        logger.info(f"Daily close: Ending balance ${ending_balance:,.2f}")
        logger.info(f"Active positions: {self.get_active_positions_count()}")
    
    def get_status_report(self) -> Dict:
        """Get comprehensive status report"""
        account = self.get_account_status()
        
        position_reports = []
        total_unrealized_pl = 0
        
        for symbol, position in self.positions.items():
            if position.is_closed():
                continue
            
            current_price = self.client.get_latest_price(symbol)
            if current_price:
                if position.side == 'long':
                    unrealized_pl = (current_price - position.entry_price) * position.current_qty
                    unrealized_pl_pct = (current_price - position.entry_price) / position.entry_price
                else:
                    unrealized_pl = (position.entry_price - current_price) * position.current_qty
                    unrealized_pl_pct = (position.entry_price - current_price) / position.entry_price
                
                total_unrealized_pl += unrealized_pl
                
                position_reports.append({
                    'symbol': symbol,
                    'qty': position.current_qty,
                    'entry_price': position.entry_price,
                    'current_price': current_price,
                    'unrealized_pl': unrealized_pl,
                    'unrealized_pl_pct': unrealized_pl_pct,
                    'profit_target': position.current_profit_target.name,
                    'stop_loss_price': position.stop_loss_price,
                    'trailing_stop_active': position.trailing_stop_active
                })
        
        return {
            'account': account,
            'previous_day_balance': self.previous_day_balance,
            'active_positions': self.get_active_positions_count(),
            'max_positions': self.max_active_trades,
            'positions': position_reports,
            'total_unrealized_pl': total_unrealized_pl,
            'timestamp': datetime.now().isoformat()
        }
    
    def print_status(self):
        """Print formatted status report"""
        report = self.get_status_report()
        
        print("\n" + "="*80)
        print("TRADENOVA STATUS REPORT")
        print("="*80)
        print(f"Account Equity: ${report['account']['equity']:,.2f}")
        print(f"Cash: ${report['account']['cash']:,.2f}")
        print(f"Buying Power: ${report['account']['buying_power']:,.2f}")
        print(f"Previous Day Balance: ${report['previous_day_balance']:,.2f}")
        print(f"Active Positions: {report['active_positions']}/{report['max_positions']}")
        print(f"Total Unrealized P/L: ${report['total_unrealized_pl']:,.2f}")
        print("\nPositions:")
        print("-"*80)
        
        for pos in report['positions']:
            pl_sign = "+" if pos['unrealized_pl'] >= 0 else ""
            print(f"{pos['symbol']:6s} | Qty: {pos['qty']:8.2f} | "
                  f"Entry: ${pos['entry_price']:8.2f} | Current: ${pos['current_price']:8.2f} | "
                  f"P/L: {pl_sign}${pos['unrealized_pl']:10.2f} ({pl_sign}{pos['unrealized_pl_pct']*100:6.2f}%) | "
                  f"Target: {pos['profit_target']:4s} | "
                  f"SL: ${pos['stop_loss_price']:8.2f}")
            if pos['trailing_stop_active']:
                print(f"  └─ Trailing Stop Active")
        
        print("="*80 + "\n")


