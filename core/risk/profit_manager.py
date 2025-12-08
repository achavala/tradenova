"""
Profit Manager
Handles TP/SL and trailing stops
"""
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ProfitManager:
    """Manages profit targets and stop losses"""
    
    def __init__(
        self,
        tp1_pct: float = 0.40,  # 40%
        tp1_exit_pct: float = 0.50,  # Exit 50% at TP1
        tp2_pct: float = 0.60,  # 60%
        tp2_exit_pct: float = 0.20,  # Exit 20% of remaining at TP2
        tp3_pct: float = 1.00,  # 100%
        tp3_exit_pct: float = 0.10,  # Exit 10% of remaining at TP3
        tp4_pct: float = 1.50,  # 150%
        tp4_exit_pct: float = 0.10,  # Exit 10% of remaining at TP4
        tp5_pct: float = 2.00,  # 200%
        tp5_exit_pct: float = 1.00,  # Full exit at TP5
        stop_loss_pct: float = 0.15,  # 15%
        trailing_stop_activation_pct: float = 1.50,  # Activate after TP4
        trailing_stop_min_profit_pct: float = 1.00  # Lock in 100% minimum
    ):
        """
        Initialize profit manager
        
        Args:
            tp1_pct through tp5_pct: Profit target percentages
            tp1_exit_pct through tp5_exit_pct: Exit percentages at each target
            stop_loss_pct: Stop loss percentage
            trailing_stop_activation_pct: When to activate trailing stop
            trailing_stop_min_profit_pct: Minimum profit to lock in
        """
        self.tp1_pct = tp1_pct
        self.tp1_exit_pct = tp1_exit_pct
        self.tp2_pct = tp2_pct
        self.tp2_exit_pct = tp2_exit_pct
        self.tp3_pct = tp3_pct
        self.tp3_exit_pct = tp3_exit_pct
        self.tp4_pct = tp4_pct
        self.tp4_exit_pct = tp4_exit_pct
        self.tp5_pct = tp5_pct
        self.tp5_exit_pct = tp5_exit_pct
        self.stop_loss_pct = stop_loss_pct
        self.trailing_stop_activation_pct = trailing_stop_activation_pct
        self.trailing_stop_min_profit_pct = trailing_stop_min_profit_pct
        
        # Track positions
        self.positions: Dict[str, Dict] = {}
    
    def add_position(
        self,
        symbol: str,
        qty: float,
        entry_price: float,
        side: str = 'long'
    ):
        """Add a position to track"""
        self.positions[symbol] = {
            'original_qty': qty,
            'current_qty': qty,
            'entry_price': entry_price,
            'side': side,
            'entry_time': datetime.now(),
            'current_tp': 0,  # 0 = none, 1-5 = TP level
            'trailing_stop_active': False,
            'trailing_stop_price': None,
            'highest_price': entry_price if side == 'long' else entry_price,
            'stop_loss_price': self._calculate_stop_loss(entry_price, side)
        }
        logger.info(f"Position added: {symbol} {side} {qty} @ ${entry_price:.2f}")
    
    def check_exits(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[Dict]:
        """
        Check if position should exit
        
        Returns:
            Exit instruction dict or None
        """
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        entry_price = pos['entry_price']
        side = pos['side']
        
        # Calculate profit percentage
        if side == 'long':
            profit_pct = (current_price - entry_price) / entry_price
        else:  # short
            profit_pct = (entry_price - current_price) / entry_price
        
        # Update highest price
        if side == 'long' and current_price > pos['highest_price']:
            pos['highest_price'] = current_price
        elif side == 'short' and current_price < pos['highest_price']:
            pos['highest_price'] = current_price
        
        # Check stop loss
        if side == 'long' and current_price <= pos['stop_loss_price']:
            return {
                'action': 'stop_loss',
                'qty': pos['current_qty'],
                'reason': f'Stop loss triggered at ${current_price:.2f}'
            }
        elif side == 'short' and current_price >= pos['stop_loss_price']:
            return {
                'action': 'stop_loss',
                'qty': pos['current_qty'],
                'reason': f'Stop loss triggered at ${current_price:.2f}'
            }
        
        # Check trailing stop
        if pos['trailing_stop_active'] and pos['trailing_stop_price']:
            if side == 'long' and current_price <= pos['trailing_stop_price']:
                return {
                    'action': 'trailing_stop',
                    'qty': pos['current_qty'],
                    'reason': f'Trailing stop triggered at ${current_price:.2f}'
                }
            elif side == 'short' and current_price >= pos['trailing_stop_price']:
                return {
                    'action': 'trailing_stop',
                    'qty': pos['current_qty'],
                    'reason': f'Trailing stop triggered at ${current_price:.2f}'
                }
        
        # Check profit targets
        exit_action = self._check_profit_targets(symbol, profit_pct, current_price)
        if exit_action:
            return exit_action
        
        # Activate trailing stop after TP4
        if profit_pct >= self.trailing_stop_activation_pct and not pos['trailing_stop_active']:
            self._activate_trailing_stop(symbol, current_price, side)
        
        return None
    
    def _check_profit_targets(
        self,
        symbol: str,
        profit_pct: float,
        current_price: float
    ) -> Optional[Dict]:
        """Check if any profit target is hit"""
        pos = self.positions[symbol]
        current_tp = pos['current_tp']
        
        # TP1: +40% - Exit 50%
        if profit_pct >= self.tp1_pct and current_tp == 0:
            exit_qty = pos['current_qty'] * self.tp1_exit_pct
            pos['current_qty'] -= exit_qty
            pos['current_tp'] = 1
            return {
                'action': 'partial_exit',
                'qty': exit_qty,
                'target': 'TP1',
                'reason': f'TP1 hit at {profit_pct*100:.2f}% profit'
            }
        
        # TP2: +60% - Exit 20% of remaining
        if profit_pct >= self.tp2_pct and current_tp == 1:
            exit_qty = pos['current_qty'] * self.tp2_exit_pct
            pos['current_qty'] -= exit_qty
            pos['current_tp'] = 2
            return {
                'action': 'partial_exit',
                'qty': exit_qty,
                'target': 'TP2',
                'reason': f'TP2 hit at {profit_pct*100:.2f}% profit'
            }
        
        # TP3: +100% - Exit 10% of remaining
        if profit_pct >= self.tp3_pct and current_tp == 2:
            exit_qty = pos['current_qty'] * self.tp3_exit_pct
            pos['current_qty'] -= exit_qty
            pos['current_tp'] = 3
            return {
                'action': 'partial_exit',
                'qty': exit_qty,
                'target': 'TP3',
                'reason': f'TP3 hit at {profit_pct*100:.2f}% profit'
            }
        
        # TP4: +150% - Exit 10% of remaining
        if profit_pct >= self.tp4_pct and current_tp == 3:
            exit_qty = pos['current_qty'] * self.tp4_exit_pct
            pos['current_qty'] -= exit_qty
            pos['current_tp'] = 4
            return {
                'action': 'partial_exit',
                'qty': exit_qty,
                'target': 'TP4',
                'reason': f'TP4 hit at {profit_pct*100:.2f}% profit'
            }
        
        # TP5: +200% - Full exit
        if profit_pct >= self.tp5_pct and current_tp == 4:
            exit_qty = pos['current_qty']
            pos['current_qty'] = 0
            pos['current_tp'] = 5
            return {
                'action': 'full_exit',
                'qty': exit_qty,
                'target': 'TP5',
                'reason': f'TP5 hit at {profit_pct*100:.2f}% profit'
            }
        
        return None
    
    def _activate_trailing_stop(self, symbol: str, current_price: float, side: str):
        """Activate trailing stop"""
        pos = self.positions[symbol]
        pos['trailing_stop_active'] = True
        
        # Set trailing stop to lock in minimum profit
        if side == 'long':
            pos['trailing_stop_price'] = pos['entry_price'] * (1 + self.trailing_stop_min_profit_pct)
        else:
            pos['trailing_stop_price'] = pos['entry_price'] * (1 - self.trailing_stop_min_profit_pct)
        
        logger.info(f"{symbol}: Trailing stop activated at ${pos['trailing_stop_price']:.2f}")
    
    def update_trailing_stop(self, symbol: str, current_price: float):
        """Update trailing stop price"""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        if not pos['trailing_stop_active']:
            return
        
        side = pos['side']
        entry_price = pos['entry_price']
        
        # Update trailing stop to follow price, but never below minimum profit
        if side == 'long':
            min_trailing_price = entry_price * (1 + self.trailing_stop_min_profit_pct)
            new_trailing_price = max(current_price * 0.95, min_trailing_price)  # 5% trailing
            if new_trailing_price > pos['trailing_stop_price']:
                pos['trailing_stop_price'] = new_trailing_price
        else:  # short
            max_trailing_price = entry_price * (1 - self.trailing_stop_min_profit_pct)
            new_trailing_price = min(current_price * 1.05, max_trailing_price)  # 5% trailing
            if new_trailing_price < pos['trailing_stop_price']:
                pos['trailing_stop_price'] = new_trailing_price
    
    def _calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """Calculate stop loss price"""
        if side == 'long':
            return entry_price * (1 - self.stop_loss_pct)
        else:
            return entry_price * (1 + self.stop_loss_pct)
    
    def remove_position(self, symbol: str):
        """Remove position from tracking"""
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"Position removed: {symbol}")

