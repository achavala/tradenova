"""
Options Broker Client
Handles options order execution via Alpaca
"""
import logging
from typing import Dict, Optional, List
from alpaca_client import AlpacaClient

logger = logging.getLogger(__name__)

class OptionsBrokerClient:
    """Options broker client for Alpaca"""
    
    def __init__(self, alpaca_client: AlpacaClient):
        """
        Initialize options broker client
        
        Args:
            alpaca_client: Alpaca client instance
        """
        self.client = alpaca_client
        self.api = alpaca_client.api
    
    def place_option_order(
        self,
        option_symbol: str,
        qty: int,
        side: str,  # 'buy' or 'sell'
        order_type: str = 'market',
        time_in_force: str = 'day',
        limit_price: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Place an options order
        
        Args:
            option_symbol: Option contract symbol
            qty: Quantity (must be integer)
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop', 'stop_limit'
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
            limit_price: Limit price (for limit orders)
            
        Returns:
            Order dictionary or None
        """
        try:
            qty = int(qty)  # Options must be whole contracts
            
            order_params = {
                'symbol': option_symbol,
                'qty': qty,
                'side': side,
                'type': order_type,
                'time_in_force': time_in_force
                # Note: No 'asset_class' needed - Alpaca detects options from symbol format
            }
            
            if limit_price:
                order_params['limit_price'] = limit_price
            
            order = self.api.submit_order(**order_params)
            
            logger.info(f"Options order placed: {side} {qty} {option_symbol} @ {order_type}")
            
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
            logger.error(f"Error placing options order for {option_symbol}: {e}")
            return None
    
    def get_option_position(self, option_symbol: str) -> Optional[Dict]:
        """Get option position"""
        try:
            position = self.api.get_position(option_symbol)
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
            logger.debug(f"No position found for {option_symbol}: {e}")
            return None
    
    def get_all_option_positions(self) -> List[Dict]:
        """Get all option positions"""
        try:
            positions = self.api.list_positions()
            # Filter for options (options symbols are longer and contain expiration/strike info)
            option_positions = [
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
                if len(pos.symbol) > 10  # Options symbols are typically longer
            ]
            return option_positions
        except Exception as e:
            logger.error(f"Error getting option positions: {e}")
            return []

