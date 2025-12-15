"""
Alpaca API Client for TradeNova
Handles all interactions with Alpaca Paper Trading API
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame
import pandas as pd

logger = logging.getLogger(__name__)

class AlpacaClient:
    """Wrapper for Alpaca Trading API"""
    
    def __init__(self, api_key: str, secret_key: str, base_url: str):
        """
        Initialize Alpaca client
        
        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            base_url: Alpaca API base URL (should NOT include /v2)
        """
        # Ensure base_url doesn't have trailing /v2 (alpaca-trade-api adds it)
        base_url = base_url.rstrip('/').rstrip('/v2')
        
        self.api = tradeapi.REST(
            api_key,
            secret_key,
            base_url,
            api_version='v2'
        )
        self.ALPACA_BASE_URL = base_url
        logger.info(f"Alpaca client initialized with base URL: {base_url}")
    
    def get_account(self) -> Dict:
        """Get account information"""
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
                'account_blocked': account.account_blocked
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            raise
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
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
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol"""
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
            logger.debug(f"No position found for {symbol}: {e}")
            return None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol"""
        try:
            bars = self.api.get_latest_bar(symbol)
            if bars:
                return float(bars.c)
            # Fallback to last trade
            trade = self.api.get_latest_trade(symbol)
            if trade:
                return float(trade.price)
            return None
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
            return None
    
    def get_historical_bars(self, symbol: str, timeframe: TimeFrame, 
                           start: datetime, end: datetime) -> pd.DataFrame:
        """Get historical bars"""
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
    
    def place_order(self, symbol: str, qty: float, side: str, 
                   order_type: str = 'market', time_in_force: str = 'day',
                   limit_price: Optional[float] = None,
                   stop_price: Optional[float] = None) -> Optional[Dict]:
        """
        Place an order
        
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
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self.api.cancel_order(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_orders(self, status: str = 'all', limit: int = 50) -> List[Dict]:
        """Get orders"""
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
    
    def is_market_open(self) -> bool:
        """Check if market is open"""
        try:
            clock = self.api.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False


