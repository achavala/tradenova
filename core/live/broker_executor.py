"""
Broker Execution Engine
Handles all order types and execution logic
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from enum import Enum

from alpaca_client import AlpacaClient
from core.live.options_broker_client import OptionsBrokerClient

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    BRACKET = "bracket"
    OCO = "oco"  # One-Cancels-Other

class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class BrokerExecutor:
    """Broker execution engine"""
    
    def __init__(self, alpaca_client: AlpacaClient):
        """
        Initialize broker executor
        
        Args:
            alpaca_client: Alpaca client instance
        """
        self.client = alpaca_client
        self.options_client = OptionsBrokerClient(alpaca_client)
        self.pending_orders: Dict[str, Dict] = {}
        self.order_history: List[Dict] = []
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        
    def execute_market_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        is_option: bool = False
    ) -> Optional[Dict]:
        """
        Execute market order
        
        Args:
            symbol: Trading symbol
            qty: Quantity
            side: 'buy' or 'sell'
            is_option: Whether this is an options order
            
        Returns:
            Order result dictionary
        """
        try:
            if is_option:
                order = self.options_client.place_option_order(
                    symbol=symbol,
                    qty=int(qty),
                    side=side,
                    order_type='market'
                )
            else:
                order = self.client.place_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    order_type='market'
                )
            
            if order:
                order['timestamp'] = datetime.now().isoformat()
                order['order_type'] = OrderType.MARKET.value
                self.order_history.append(order)
                logger.info(f"Market order executed: {side} {qty} {symbol}")
            
            return order
            
        except Exception as e:
            logger.error(f"Error executing market order: {e}")
            return self._retry_order('market', symbol, qty, side, is_option)
    
    def execute_limit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        limit_price: float,
        is_option: bool = False,
        time_in_force: str = 'day'
    ) -> Optional[Dict]:
        """
        Execute limit order
        
        Args:
            symbol: Trading symbol
            qty: Quantity
            side: 'buy' or 'sell'
            limit_price: Limit price
            is_option: Whether this is an options order
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
            
        Returns:
            Order result dictionary
        """
        try:
            if is_option:
                order = self.options_client.place_option_order(
                    symbol=symbol,
                    qty=int(qty),
                    side=side,
                    order_type='limit',
                    limit_price=limit_price,
                    time_in_force=time_in_force
                )
            else:
                order = self.client.place_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    order_type='limit',
                    limit_price=limit_price,
                    time_in_force=time_in_force
                )
            
            if order:
                order['timestamp'] = datetime.now().isoformat()
                order['order_type'] = OrderType.LIMIT.value
                order['limit_price'] = limit_price
                self.pending_orders[order['id']] = order
                self.order_history.append(order)
                logger.info(f"Limit order placed: {side} {qty} {symbol} @ ${limit_price:.2f}")
            
            return order
            
        except Exception as e:
            logger.error(f"Error executing limit order: {e}")
            return self._retry_order('limit', symbol, qty, side, is_option, limit_price=limit_price)
    
    def execute_bracket_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        entry_price: float,
        take_profit: float,
        stop_loss: float,
        is_option: bool = False
    ) -> Optional[Dict]:
        """
        Execute bracket order (entry + TP + SL)
        
        Note: Alpaca may not support bracket orders directly
        This implementation places entry order and sets up TP/SL
        
        Args:
            symbol: Trading symbol
            qty: Quantity
            side: 'buy' or 'sell'
            entry_price: Entry price
            take_profit: Take profit price
            stop_loss: Stop loss price
            is_option: Whether this is an options order
            
        Returns:
            Order result dictionary
        """
        try:
            # Place entry order
            if entry_price:
                entry_order = self.execute_limit_order(
                    symbol, qty, side, entry_price, is_option
                )
            else:
                entry_order = self.execute_market_order(
                    symbol, qty, side, is_option
                )
            
            if not entry_order:
                return None
            
            # Store bracket info for TP/SL management
            bracket_info = {
                'entry_order_id': entry_order['id'],
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'is_option': is_option,
                'timestamp': datetime.now().isoformat()
            }
            
            entry_order['bracket_info'] = bracket_info
            self.pending_orders[entry_order['id']] = entry_order
            
            logger.info(f"Bracket order placed: Entry @ ${entry_price:.2f}, "
                       f"TP @ ${take_profit:.2f}, SL @ ${stop_loss:.2f}")
            
            return entry_order
            
        except Exception as e:
            logger.error(f"Error executing bracket order: {e}")
            return None
    
    def execute_oco_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        price1: float,
        price2: float,
        is_option: bool = False
    ) -> Optional[Dict]:
        """
        Execute OCO (One-Cancels-Other) order
        
        Note: Alpaca may not support OCO directly
        This is a simplified implementation
        
        Args:
            symbol: Trading symbol
            qty: Quantity
            side: 'buy' or 'sell'
            price1: First limit price
            price2: Second limit price
            is_option: Whether this is an options order
            
        Returns:
            Order result dictionary
        """
        try:
            # Place first order
            order1 = self.execute_limit_order(symbol, qty, side, price1, is_option)
            
            if not order1:
                return None
            
            # Store OCO relationship
            oco_info = {
                'order1_id': order1['id'],
                'price1': price1,
                'price2': price2,
                'symbol': symbol,
                'qty': qty,
                'side': side
            }
            
            order1['oco_info'] = oco_info
            self.pending_orders[order1['id']] = order1
            
            logger.info(f"OCO order placed: {side} {qty} {symbol} @ ${price1:.2f} or ${price2:.2f}")
            
            return order1
            
        except Exception as e:
            logger.error(f"Error executing OCO order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            success = self.client.cancel_order(order_id)
            
            if success and order_id in self.pending_orders:
                self.pending_orders[order_id]['status'] = OrderStatus.CANCELLED.value
                logger.info(f"Order {order_id} cancelled")
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def cancel_stale_orders(self, max_age_minutes: int = 30) -> int:
        """
        Cancel orders that are older than max_age_minutes
        
        Args:
            max_age_minutes: Maximum age in minutes
            
        Returns:
            Number of orders cancelled
        """
        cancelled = 0
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        
        for order_id, order in list(self.pending_orders.items()):
            order_time = datetime.fromisoformat(order.get('timestamp', ''))
            
            if order_time < cutoff_time:
                if self.cancel_order(order_id):
                    cancelled += 1
        
        if cancelled > 0:
            logger.info(f"Cancelled {cancelled} stale orders")
        
        return cancelled
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get current order status"""
        try:
            orders = self.client.get_orders()
            for order in orders:
                if order['id'] == order_id:
                    # Update pending orders
                    if order_id in self.pending_orders:
                        self.pending_orders[order_id].update(order)
                    return order
            return None
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None
    
    def _retry_order(
        self,
        order_type: str,
        symbol: str,
        qty: float,
        side: str,
        is_option: bool,
        **kwargs
    ) -> Optional[Dict]:
        """Retry order execution"""
        import time
        
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.retry_delay * (attempt + 1))
                
                if order_type == 'market':
                    return self.execute_market_order(symbol, qty, side, is_option)
                elif order_type == 'limit':
                    return self.execute_limit_order(
                        symbol, qty, side, kwargs.get('limit_price'), is_option
                    )
            except Exception as e:
                logger.warning(f"Retry {attempt + 1} failed: {e}")
        
        logger.error(f"Failed to execute {order_type} order after {self.max_retries} retries")
        return None
    
    def get_position_book(self) -> Dict:
        """Get current positions with details"""
        try:
            positions = self.client.get_positions()
            
            position_book = {}
            for pos in positions:
                symbol = pos['symbol']
                position_book[symbol] = {
                    'qty': pos['qty'],
                    'avg_entry_price': pos['avg_entry_price'],
                    'current_price': pos['current_price'],
                    'market_value': pos['market_value'],
                    'unrealized_pl': pos['unrealized_pl'],
                    'unrealized_plpc': pos['unrealized_plpc']
                }
            
            return position_book
            
        except Exception as e:
            logger.error(f"Error getting position book: {e}")
            return {}
    
    def get_account_status(self) -> Dict:
        """Get account status"""
        return self.client.get_account()

