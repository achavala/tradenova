"""
Alpaca API Client for TradeNova
Handles all interactions with Alpaca Paper Trading API with robust retry logic
"""
import logging
import time
import random
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime, timedelta
from functools import wraps
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame
import pandas as pd

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,),
    non_retryable_patterns: list = None
):
    """
    Decorator for API calls with exponential backoff retry
    
    Args:
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        retryable_exceptions: Tuple of exception types to retry
        non_retryable_patterns: List of error message patterns that should not be retried
    """
    if non_retryable_patterns is None:
        non_retryable_patterns = ['unauthorized', 'forbidden', 'invalid', 'not found']
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except retryable_exceptions as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    # Check for non-retryable errors
                    if any(pattern in error_str for pattern in non_retryable_patterns):
                        logger.error(f"Non-retryable error in {func.__name__}: {e}")
                        raise
                    
                    if attempt < max_retries:
                        # Calculate delay with exponential backoff and jitter
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        delay = delay * (0.8 + random.random() * 0.4)
                        
                        logger.warning(
                            f"API call {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}: {e}")
                        raise
            
            raise last_exception
        
        return wrapper
    return decorator


class AlpacaClient:
    """Wrapper for Alpaca Trading API with robust error handling"""
    
    def __init__(self, api_key: str = None, secret_key: str = None, base_url: str = None, paper: bool = True):
        """
        Initialize Alpaca client
        
        Args:
            api_key: Alpaca API key (or load from env)
            secret_key: Alpaca secret key (or load from env)
            base_url: Alpaca API base URL (or load from env)
            paper: Use paper trading (default True)
        """
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        # Get credentials from environment if not provided
        api_key = api_key or os.getenv('ALPACA_API_KEY', '')
        secret_key = secret_key or os.getenv('ALPACA_SECRET_KEY', '')
        
        if paper:
            base_url = base_url or os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        else:
            base_url = base_url or os.getenv('ALPACA_LIVE_BASE_URL', 'https://api.alpaca.markets')
        
        # Ensure base_url doesn't have trailing /v2 (alpaca-trade-api adds it)
        base_url = base_url.rstrip('/').rstrip('/v2')
        
        self.api = tradeapi.REST(
            api_key,
            secret_key,
            base_url,
            api_version='v2'
        )
        self.ALPACA_BASE_URL = base_url
        self._connection_verified = False
        
        # Verify connection on init
        try:
            self._verify_connection()
            logger.info(f"Alpaca client initialized (base URL: {base_url})")
        except Exception as e:
            logger.warning(f"Alpaca client initialized but connection check failed: {e}")
    
    def _verify_connection(self):
        """Verify API connection is working"""
        try:
            self.api.get_clock()
            self._connection_verified = True
        except Exception as e:
            self._connection_verified = False
            raise ConnectionError(f"Failed to connect to Alpaca API: {e}")
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_account(self) -> Dict:
        """Get account information with retry"""
        try:
            account = self.api.get_account()
            return {
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'day_trading_buying_power': float(account.daytrading_buying_power),
                'portfolio_value': float(account.portfolio_value),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'account_blocked': account.account_blocked,
                'status': getattr(account, 'status', 'unknown')
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            raise
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_positions(self) -> List[Dict]:
        """Get all open positions with retry"""
        try:
            positions = self.api.list_positions()
            return [
                {
                    'symbol': pos.symbol,
                    'qty': float(pos.qty),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'side': pos.side
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    @retry_with_backoff(max_retries=2, base_delay=0.5)
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol with retry"""
        try:
            position = self.api.get_position(symbol)
            return {
                'symbol': position.symbol,
                'qty': float(position.qty),
                'avg_entry_price': float(position.avg_entry_price),
                'current_price': float(position.current_price),
                'market_value': float(position.market_value),
                'cost_basis': float(position.cost_basis),
                'unrealized_pl': float(position.unrealized_pl),
                'unrealized_plpc': float(position.unrealized_plpc),
                'side': position.side
            }
        except Exception as e:
            error_str = str(e).lower()
            if 'not found' in error_str or 'does not exist' in error_str:
                logger.debug(f"No position found for {symbol}")
            else:
                logger.debug(f"No position found for {symbol}: {e}")
            return None
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol with retry"""
        try:
            # Try getting latest bar first
            try:
                bars = self.api.get_latest_bar(symbol)
                if bars:
                    return float(bars.c)
            except:
                pass
            
            # Fallback to last trade
            trade = self.api.get_latest_trade(symbol)
            if trade:
                return float(trade.price)
            return None
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
            return None
    
    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def get_historical_bars(self, symbol: str, timeframe: TimeFrame, 
                           start: datetime, end: datetime) -> pd.DataFrame:
        """Get historical bars with retry"""
        try:
            # Format dates as strings in YYYY-MM-DD format for Alpaca
            start_str = start.strftime('%Y-%m-%d')
            end_str = end.strftime('%Y-%m-%d')
            
            bars = self.api.get_bars(
                symbol,
                timeframe,
                start_str,
                end_str
            ).df
            return bars
        except Exception as e:
            logger.error(f"Error getting historical bars for {symbol}: {e}")
            return pd.DataFrame()
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def place_order(self, symbol: str, qty: float, side: str, 
                   order_type: str = 'market', time_in_force: str = 'day',
                   limit_price: Optional[float] = None,
                   stop_price: Optional[float] = None) -> Optional[Dict]:
        """
        Place an order with retry logic
        
        Args:
            symbol: Stock symbol
            qty: Quantity to trade
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop', 'stop_limit'
            time_in_force: 'day', 'gtc', 'opg', 'cls', 'ioc', 'fok'
            limit_price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
        """
        try:
            qty = int(qty) if qty >= 1 else qty
            
            order_params = {
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'type': order_type,
                'time_in_force': time_in_force
            }
            
            if limit_price:
                order_params['limit_price'] = limit_price
            if stop_price:
                order_params['stop_price'] = stop_price
            
            order = self.api.submit_order(**order_params)
            
            logger.info(f"Order placed: {side} {qty} {symbol} @ {order_type}")
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
            }
        except Exception as e:
            logger.error(f"Error placing order for {symbol}: {e}")
            raise
    
    @retry_with_backoff(max_retries=2, base_delay=0.5)
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order with retry"""
        try:
            self.api.cancel_order(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def get_orders(self, status: str = 'all', limit: int = 50) -> List[Dict]:
        """Get orders with retry"""
        try:
            orders = self.api.list_orders(status=status, limit=limit)
            return [
                {
                    'id': order.id,
                    'symbol': order.symbol,
                    'qty': float(order.qty),
                    'side': order.side,
                    'type': order.type,
                    'status': order.status,
                    'filled_qty': float(order.filled_qty) if order.filled_qty else 0,
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def is_market_open(self) -> bool:
        """Check if market is open with retry"""
        try:
            clock = self.api.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def get_clock(self) -> Dict:
        """Get market clock info with retry"""
        try:
            clock = self.api.get_clock()
            return {
                'is_open': clock.is_open,
                'next_open': clock.next_open.isoformat() if clock.next_open else None,
                'next_close': clock.next_close.isoformat() if clock.next_close else None,
                'timestamp': clock.timestamp.isoformat() if clock.timestamp else None
            }
        except Exception as e:
            logger.error(f"Error getting clock: {e}")
            return {'is_open': False}
    
    def health_check(self) -> Dict:
        """Perform a health check on the API connection"""
        result = {
            'connected': False,
            'account_accessible': False,
            'market_status': None,
            'errors': []
        }
        
        try:
            # Test clock endpoint (lightweight)
            clock = self.get_clock()
            result['connected'] = True
            result['market_status'] = 'open' if clock.get('is_open') else 'closed'
        except Exception as e:
            result['errors'].append(f"Clock check failed: {e}")
        
        try:
            # Test account endpoint
            account = self.get_account()
            if account:
                result['account_accessible'] = True
        except Exception as e:
            result['errors'].append(f"Account check failed: {e}")
        
        return result
