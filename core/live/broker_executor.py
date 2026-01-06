"""
Broker Execution Engine
Handles all order types and execution logic with robust retry and error handling
"""
import logging
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps

from alpaca_client import AlpacaClient
from core.live.options_broker_client import OptionsBrokerClient

logger = logging.getLogger(__name__)


def exponential_backoff_retry(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
    """
    Decorator for exponential backoff retry logic
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        # Add some jitter (±20%)
                        import random
                        delay = delay * (0.8 + random.random() * 0.4)
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
            
            # Re-raise the last exception if all retries failed
            raise last_exception
        
        return wrapper
    return decorator


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
    """Broker execution engine with robust error handling"""
    
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
        self.base_retry_delay = 1.0
        self.max_retry_delay = 30.0
        
    def execute_market_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        is_option: bool = False
    ) -> Optional[Dict]:
        """
        Execute market order with retry logic
        
        Args:
            symbol: Trading symbol (stock ticker or options contract symbol)
            qty: Quantity
            side: 'buy' or 'sell'
            is_option: Whether this is an options order
            
        Returns:
            Order result dictionary or None on failure
        """
        return self._execute_with_retry(
            order_type='market',
            symbol=symbol,
            qty=qty,
            side=side,
            is_option=is_option
        )
    
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
        Execute limit order with retry logic
        
        Args:
            symbol: Trading symbol
            qty: Quantity
            side: 'buy' or 'sell'
            limit_price: Limit price
            is_option: Whether this is an options order
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
            
        Returns:
            Order result dictionary or None on failure
        """
        return self._execute_with_retry(
            order_type='limit',
            symbol=symbol,
            qty=qty,
            side=side,
            is_option=is_option,
            limit_price=limit_price,
            time_in_force=time_in_force
        )
    
    def _execute_with_retry(
        self,
        order_type: str,
        symbol: str,
        qty: float,
        side: str,
        is_option: bool,
        **kwargs
    ) -> Optional[Dict]:
        """
        Execute order with exponential backoff retry
        
        Args:
            order_type: 'market' or 'limit'
            symbol: Trading symbol
            qty: Quantity
            side: 'buy' or 'sell'
            is_option: Whether this is an options order
            **kwargs: Additional order parameters (limit_price, time_in_force, etc.)
            
        Returns:
            Order result dictionary or None on failure
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if order_type == 'market':
                    order = self._place_market_order(symbol, qty, side, is_option)
                elif order_type == 'limit':
                    order = self._place_limit_order(
                        symbol, qty, side, is_option,
                        kwargs.get('limit_price'),
                        kwargs.get('time_in_force', 'day')
                    )
                else:
                    raise ValueError(f"Unknown order type: {order_type}")
                
                if order:
                    order['timestamp'] = datetime.now().isoformat()
                    order['order_type'] = order_type
                    if order_type == 'limit':
                        order['limit_price'] = kwargs.get('limit_price')
                    
                    self.order_history.append(order)
                    logger.info(f"Order executed successfully: {side} {qty} {symbol} ({order_type})")
                    return order
                else:
                    raise RuntimeError(f"Order returned None for {symbol}")
                    
            except Exception as e:
                last_exception = e
                error_str = str(e)
                
                # Check if this is a non-retryable error
                non_retryable_errors = [
                    'insufficient',
                    'invalid symbol',
                    'market closed',
                    'unauthorized',
                    'forbidden'
                ]
                
                is_non_retryable = any(err in error_str.lower() for err in non_retryable_errors)
                
                if is_non_retryable:
                    logger.error(f"Non-retryable error for {symbol}: {e}")
                    break
                
                if attempt < self.max_retries:
                    # Calculate exponential backoff delay
                    delay = min(
                        self.base_retry_delay * (2 ** attempt),
                        self.max_retry_delay
                    )
                    # Add jitter (±20%)
                    import random
                    delay = delay * (0.8 + random.random() * 0.4)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries + 1} failed for {symbol}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed for {symbol}: {e}")
        
        return None
    
    def _place_market_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        is_option: bool
    ) -> Optional[Dict]:
        """Place a market order (single attempt, no retry)"""
        if is_option:
            # Options order - use options client
            order = self.options_client.place_option_order(
                option_symbol=symbol,
                qty=int(qty),
                side=side,
                order_type='market'
            )
        else:
            # Stock order - use regular client
            order = self.client.place_order(
                symbol=symbol,
                qty=qty,
                side=side,
                order_type='market'
            )
        
        return order
    
    def _place_limit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        is_option: bool,
        limit_price: float,
        time_in_force: str = 'day'
    ) -> Optional[Dict]:
        """Place a limit order (single attempt, no retry)"""
        if is_option:
            # Options order
            order = self.options_client.place_option_order(
                option_symbol=symbol,
                qty=int(qty),
                side=side,
                order_type='limit',
                limit_price=limit_price,
                time_in_force=time_in_force
            )
        else:
            # Stock order
            order = self.client.place_order(
                symbol=symbol,
                qty=qty,
                side=side,
                order_type='limit',
                limit_price=limit_price,
                time_in_force=time_in_force
            )
        
        if order and is_option is False:
            self.pending_orders[order['id']] = order
        
        return order
    
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
            try:
                order_time = datetime.fromisoformat(order.get('timestamp', ''))
                
                if order_time < cutoff_time:
                    if self.cancel_order(order_id):
                        cancelled += 1
            except (ValueError, TypeError):
                continue
        
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
