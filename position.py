"""
Position Management for TradeNova
Handles individual position tracking, profit targets, and stop losses
"""
import logging
from typing import Optional, Dict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ProfitTarget(Enum):
    """Profit target levels"""
    NONE = 0
    TP1 = 1
    TP2 = 2
    TP3 = 3
    TP4 = 4
    TP5 = 5

class Position:
    """Represents a trading position with profit targets and stop loss"""
    
    def __init__(self, symbol: str, qty: float, entry_price: float, 
                 side: str = 'long', config: Optional[Dict] = None):
        """
        Initialize position
        
        Args:
            symbol: Stock symbol
            qty: Quantity
            entry_price: Entry price
            side: 'long' or 'short'
            config: Configuration dictionary with profit targets and stop loss
        """
        self.symbol = symbol
        self.original_qty = qty
        self.current_qty = qty
        self.entry_price = entry_price
        self.side = side
        self.entry_time = datetime.now()
        
        # Configuration
        self.config = config or {}
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.15)
        self.tp1_pct = self.config.get('tp1_pct', 0.40)
        self.tp2_pct = self.config.get('tp2_pct', 0.60)
        self.tp3_pct = self.config.get('tp3_pct', 1.00)
        self.tp4_pct = self.config.get('tp4_pct', 1.50)
        self.tp5_pct = self.config.get('tp5_pct', 2.00)
        
        # Exit percentages
        self.tp1_exit_pct = self.config.get('tp1_exit_pct', 0.50)
        self.tp2_exit_pct = self.config.get('tp2_exit_pct', 0.20)
        self.tp3_exit_pct = self.config.get('tp3_exit_pct', 0.10)
        self.tp4_exit_pct = self.config.get('tp4_exit_pct', 0.10)
        self.tp5_exit_pct = self.config.get('tp5_exit_pct', 1.00)
        
        # Trailing stop
        self.trailing_stop_activation_pct = self.config.get('trailing_stop_activation_pct', 1.50)
        self.trailing_stop_min_profit_pct = self.config.get('trailing_stop_min_profit_pct', 1.00)
        
        # State tracking
        self.current_profit_target = ProfitTarget.NONE
        self.highest_price = entry_price
        self.trailing_stop_active = False
        self.trailing_stop_price = None
        self.stop_loss_price = self._calculate_stop_loss()
        
        # Calculated targets
        self.tp1_price = entry_price * (1 + self.tp1_pct) if side == 'long' else entry_price * (1 - self.tp1_pct)
        self.tp2_price = entry_price * (1 + self.tp2_pct) if side == 'long' else entry_price * (1 - self.tp2_pct)
        self.tp3_price = entry_price * (1 + self.tp3_pct) if side == 'long' else entry_price * (1 - self.tp3_pct)
        self.tp4_price = entry_price * (1 + self.tp4_pct) if side == 'long' else entry_price * (1 - self.tp4_pct)
        self.tp5_price = entry_price * (1 + self.tp5_pct) if side == 'long' else entry_price * (1 - self.tp5_pct)
        
        logger.info(f"Position created: {symbol} {side} {qty} @ {entry_price:.2f}")
    
    def _calculate_stop_loss(self) -> float:
        """Calculate stop loss price"""
        if self.side == 'long':
            return self.entry_price * (1 - self.stop_loss_pct)
        else:
            return self.entry_price * (1 + self.stop_loss_pct)
    
    def update_price(self, current_price: float) -> Dict:
        """
        Update position with current price and check for exits
        
        Returns:
            Dict with action information if exit is needed
        """
        if self.side == 'long':
            profit_pct = (current_price - self.entry_price) / self.entry_price
        else:
            profit_pct = (self.entry_price - current_price) / self.entry_price
        
        # Update highest price for trailing stop
        if self.side == 'long' and current_price > self.highest_price:
            self.highest_price = current_price
        elif self.side == 'short' and current_price < self.highest_price:
            self.highest_price = current_price
        
        # Check stop loss
        if self.side == 'long' and current_price <= self.stop_loss_price:
            return {
                'action': 'stop_loss',
                'qty': self.current_qty,
                'reason': f'Stop loss triggered at {current_price:.2f}'
            }
        elif self.side == 'short' and current_price >= self.stop_loss_price:
            return {
                'action': 'stop_loss',
                'qty': self.current_qty,
                'reason': f'Stop loss triggered at {current_price:.2f}'
            }
        
        # Check trailing stop
        if self.trailing_stop_active and self.trailing_stop_price:
            if self.side == 'long' and current_price <= self.trailing_stop_price:
                return {
                    'action': 'trailing_stop',
                    'qty': self.current_qty,
                    'reason': f'Trailing stop triggered at {current_price:.2f}'
                }
            elif self.side == 'short' and current_price >= self.trailing_stop_price:
                return {
                    'action': 'trailing_stop',
                    'qty': self.current_qty,
                    'reason': f'Trailing stop triggered at {current_price:.2f}'
                }
        
        # Check profit targets
        exit_action = self._check_profit_targets(current_price, profit_pct)
        if exit_action:
            return exit_action
        
        # Update trailing stop if TP4 reached
        if profit_pct >= self.trailing_stop_activation_pct and not self.trailing_stop_active:
            self._activate_trailing_stop(current_price)
        
        return {'action': 'hold'}
    
    def _check_profit_targets(self, current_price: float, profit_pct: float) -> Optional[Dict]:
        """Check if any profit target is hit"""
        
        # TP1: +40% - Sell 50% of position
        if profit_pct >= self.tp1_pct and self.current_profit_target == ProfitTarget.NONE:
            exit_qty = self.current_qty * self.tp1_exit_pct
            self.current_qty -= exit_qty
            self.current_profit_target = ProfitTarget.TP1
            logger.info(f"{self.symbol} TP1 hit: Exiting {exit_qty:.2f} shares ({self.tp1_exit_pct*100}%)")
            return {
                'action': 'partial_exit',
                'qty': exit_qty,
                'target': 'TP1',
                'reason': f'TP1 hit at {profit_pct*100:.2f}% profit'
            }
        
        # TP2: +60% - Sell 20% of remaining
        if profit_pct >= self.tp2_pct and self.current_profit_target == ProfitTarget.TP1:
            exit_qty = self.current_qty * self.tp2_exit_pct
            self.current_qty -= exit_qty
            self.current_profit_target = ProfitTarget.TP2
            logger.info(f"{self.symbol} TP2 hit: Exiting {exit_qty:.2f} shares ({self.tp2_exit_pct*100}%)")
            return {
                'action': 'partial_exit',
                'qty': exit_qty,
                'target': 'TP2',
                'reason': f'TP2 hit at {profit_pct*100:.2f}% profit'
            }
        
        # TP3: +100% - Sell 10% of remaining
        if profit_pct >= self.tp3_pct and self.current_profit_target == ProfitTarget.TP2:
            exit_qty = self.current_qty * self.tp3_exit_pct
            self.current_qty -= exit_qty
            self.current_profit_target = ProfitTarget.TP3
            logger.info(f"{self.symbol} TP3 hit: Exiting {exit_qty:.2f} shares ({self.tp3_exit_pct*100}%)")
            return {
                'action': 'partial_exit',
                'qty': exit_qty,
                'target': 'TP3',
                'reason': f'TP3 hit at {profit_pct*100:.2f}% profit'
            }
        
        # TP4: +150% - Sell 10% of remaining
        if profit_pct >= self.tp4_pct and self.current_profit_target == ProfitTarget.TP3:
            exit_qty = self.current_qty * self.tp4_exit_pct
            self.current_qty -= exit_qty
            self.current_profit_target = ProfitTarget.TP4
            logger.info(f"{self.symbol} TP4 hit: Exiting {exit_qty:.2f} shares ({self.tp4_exit_pct*100}%)")
            return {
                'action': 'partial_exit',
                'qty': exit_qty,
                'target': 'TP4',
                'reason': f'TP4 hit at {profit_pct*100:.2f}% profit'
            }
        
        # TP5: +200% - Full exit
        if profit_pct >= self.tp5_pct and self.current_profit_target == ProfitTarget.TP4:
            exit_qty = self.current_qty
            self.current_qty = 0
            self.current_profit_target = ProfitTarget.TP5
            logger.info(f"{self.symbol} TP5 hit: Full exit {exit_qty:.2f} shares")
            return {
                'action': 'full_exit',
                'qty': exit_qty,
                'target': 'TP5',
                'reason': f'TP5 hit at {profit_pct*100:.2f}% profit'
            }
        
        return None
    
    def _activate_trailing_stop(self, current_price: float):
        """Activate trailing stop after TP4"""
        self.trailing_stop_active = True
        # Set trailing stop to lock in minimum profit
        if self.side == 'long':
            self.trailing_stop_price = self.entry_price * (1 + self.trailing_stop_min_profit_pct)
        else:
            self.trailing_stop_price = self.entry_price * (1 - self.trailing_stop_min_profit_pct)
        logger.info(f"{self.symbol} Trailing stop activated at {self.trailing_stop_price:.2f}")
    
    def update_trailing_stop(self, current_price: float):
        """Update trailing stop price to lock in profits"""
        if not self.trailing_stop_active:
            return
        
        # Update trailing stop to follow price, but never below minimum profit
        if self.side == 'long':
            min_trailing_price = self.entry_price * (1 + self.trailing_stop_min_profit_pct)
            new_trailing_price = max(current_price * 0.95, min_trailing_price)  # 5% trailing
            if new_trailing_price > self.trailing_stop_price:
                self.trailing_stop_price = new_trailing_price
        else:
            max_trailing_price = self.entry_price * (1 - self.trailing_stop_min_profit_pct)
            new_trailing_price = min(current_price * 1.05, max_trailing_price)  # 5% trailing
            if new_trailing_price < self.trailing_stop_price:
                self.trailing_stop_price = new_trailing_price
    
    def get_status(self) -> Dict:
        """Get current position status"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'original_qty': self.original_qty,
            'current_qty': self.current_qty,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat(),
            'current_profit_target': self.current_profit_target.name,
            'stop_loss_price': self.stop_loss_price,
            'trailing_stop_active': self.trailing_stop_active,
            'trailing_stop_price': self.trailing_stop_price,
            'highest_price': self.highest_price
        }
    
    def is_closed(self) -> bool:
        """Check if position is fully closed"""
        return self.current_qty <= 0.01  # Account for floating point precision


