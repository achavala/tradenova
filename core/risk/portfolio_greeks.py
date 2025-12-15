"""
Portfolio Greeks Aggregator
Aggregates Delta, Gamma, Theta, and Vega across all open positions.

This is Step 1 of the Portfolio Risk Layer implementation.
Sits above all trading decisions to provide portfolio-level risk visibility.
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PortfolioGreeks:
    """Portfolio-level Greeks aggregation"""
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0  # Per day
    vega: float = 0.0
    timestamp: datetime = None
    positions_count: int = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'delta': round(self.delta, 2),
            'gamma': round(self.gamma, 4),
            'theta': round(self.theta, 2),
            'vega': round(self.vega, 2),
            'timestamp': self.timestamp.isoformat(),
            'positions_count': self.positions_count
        }


class PortfolioGreeksAggregator:
    """
    Aggregates Greeks across all open positions.
    
    Handles:
    - Stock positions (no Greeks, contribute 0)
    - Options positions (with Greeks from database/API)
    - Multiple tickers, expiries, strikes
    """
    
    def __init__(self, massive_feed=None):
        """
        Initialize aggregator
        
        Args:
            massive_feed: Optional MassiveDataFeed instance for fetching Greeks
        """
        self.massive_feed = massive_feed
        self.last_update = None
        self._greeks_cache = {}  # Cache Greeks by (symbol, strike, expiry, type)
    
    def aggregate_greeks(
        self,
        positions: List[Dict],
        current_prices: Optional[Dict[str, float]] = None
    ) -> PortfolioGreeks:
        """
        Aggregate Greeks across all positions
        
        Args:
            positions: List of position dictionaries. Each position should have:
                - symbol: str
                - qty: float (positive for long, negative for short)
                - entry_price: float
                - side: 'long' or 'short'
                - option_type: Optional[str] - 'call' or 'put' (if options position)
                - strike: Optional[float] - Strike price (if options position)
                - expiration_date: Optional[str] - Expiration date (if options position)
                - delta: Optional[float] - Delta (if already known)
                - gamma: Optional[float] - Gamma (if already known)
                - theta: Optional[float] - Theta (if already known)
                - vega: Optional[float] - Vega (if already known)
            current_prices: Optional dict of current prices by symbol
        
        Returns:
            PortfolioGreeks object with aggregated values
        """
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        positions_count = 0
        
        for pos in positions:
            symbol = pos.get('symbol')
            qty = pos.get('qty', 0)
            side = pos.get('side', 'long')
            option_type = pos.get('option_type')
            strike = pos.get('strike')
            expiration_date = pos.get('expiration_date')
            
            # Skip closed positions
            if abs(qty) < 0.01:
                continue
            
            # Determine position multiplier (long = +1, short = -1)
            position_multiplier = 1.0 if side == 'long' else -1.0
            
            # Get Greeks for this position
            greeks = self._get_position_greeks(
                pos=pos,
                symbol=symbol,
                qty=qty,
                option_type=option_type,
                strike=strike,
                expiration_date=expiration_date,
                current_prices=current_prices
            )
            
            if greeks:
                # Aggregate: multiply by quantity and position direction
                # For options: qty is in contracts, each contract = 100 shares
                contract_multiplier = 100.0 if option_type else 1.0
                
                total_delta += greeks['delta'] * qty * position_multiplier * contract_multiplier
                total_gamma += greeks['gamma'] * qty * position_multiplier * contract_multiplier
                total_theta += greeks['theta'] * qty * position_multiplier * contract_multiplier
                total_vega += greeks['vega'] * qty * position_multiplier * contract_multiplier
                positions_count += 1
            else:
                # Stock position or no Greeks available
                # For stock positions, Delta = 1.0 (1:1 with underlying)
                if not option_type:
                    # Stock position: Delta = 1.0, other Greeks = 0
                    total_delta += qty * position_multiplier
                    positions_count += 1
        
        result = PortfolioGreeks(
            delta=total_delta,
            gamma=total_gamma,
            theta=total_theta,
            vega=total_vega,
            timestamp=datetime.now(),
            positions_count=positions_count
        )
        
        self.last_update = result.timestamp
        logger.debug(f"Portfolio Greeks: Δ={total_delta:.2f}, Γ={total_gamma:.4f}, Θ={total_theta:.2f}, Vega={total_vega:.2f}")
        
        return result
    
    def _get_position_greeks(
        self,
        pos: Dict,
        symbol: str,
        qty: float,
        option_type: Optional[str],
        strike: Optional[float],
        expiration_date: Optional[str],
        current_prices: Optional[Dict[str, float]]
    ) -> Optional[Dict[str, float]]:
        """
        Get Greeks for a single position
        
        Returns:
            Dict with 'delta', 'gamma', 'theta', 'vega' or None if not available
        """
        # If Greeks are already in position dict, use them
        if all(key in pos for key in ['delta', 'gamma', 'theta', 'vega']):
            return {
                'delta': float(pos.get('delta', 0)),
                'gamma': float(pos.get('gamma', 0)),
                'theta': float(pos.get('theta', 0)),
                'vega': float(pos.get('vega', 0))
            }
        
        # If not options position, return None (will be handled as stock)
        if not option_type or not strike or not expiration_date:
            return None
        
        # Try to fetch from cache or API
        cache_key = (symbol, strike, expiration_date, option_type)
        if cache_key in self._greeks_cache:
            return self._greeks_cache[cache_key]
        
        # Try to fetch from Massive API if available
        if self.massive_feed and self.massive_feed.is_available():
            try:
                current_price = current_prices.get(symbol) if current_prices else None
                greeks = self._fetch_greeks_from_api(
                    symbol=symbol,
                    strike=strike,
                    expiration_date=expiration_date,
                    option_type=option_type,
                    current_price=current_price
                )
                if greeks:
                    self._greeks_cache[cache_key] = greeks
                    return greeks
            except Exception as e:
                logger.debug(f"Error fetching Greeks from API for {symbol}: {e}")
        
        # If no Greeks available, return None (will be handled as stock or skipped)
        return None
    
    def _fetch_greeks_from_api(
        self,
        symbol: str,
        strike: float,
        expiration_date: str,
        option_type: str,
        current_price: Optional[float]
    ) -> Optional[Dict[str, float]]:
        """
        Fetch Greeks from Massive API
        
        Returns:
            Dict with Greeks or None if not found
        """
        try:
            # Get options chain for today
            chain = self.massive_feed.get_options_chain(
                symbol=symbol,
                expiration_date=expiration_date,
                date=None,  # Current date
                use_cache=True
            )
            
            # Find matching contract
            for contract in chain:
                if (abs(contract.get('strike', 0) - strike) < 0.01 and
                    contract.get('option_type', '').lower() == option_type.lower()):
                    return {
                        'delta': float(contract.get('delta', 0)),
                        'gamma': float(contract.get('gamma', 0)),
                        'theta': float(contract.get('theta', 0)),
                        'vega': float(contract.get('vega', 0))
                    }
        except Exception as e:
            logger.debug(f"Error fetching Greeks from API: {e}")
        
        return None
    
    def get_greeks_for_position_list(
        self,
        position_list: List[Dict],
        current_prices: Optional[Dict[str, float]] = None
    ) -> PortfolioGreeks:
        """
        Convenience method to aggregate Greeks from a list of positions
        
        This is the main entry point for getting portfolio Greeks.
        """
        return self.aggregate_greeks(positions=position_list, current_prices=current_prices)
    
    def clear_cache(self):
        """Clear Greeks cache"""
        self._greeks_cache.clear()
        logger.debug("Greeks cache cleared")


# Convenience function for easy import
def get_portfolio_greeks(
    positions: List[Dict],
    massive_feed=None,
    current_prices: Optional[Dict[str, float]] = None
) -> PortfolioGreeks:
    """
    Convenience function to get portfolio Greeks
    
    Args:
        positions: List of position dictionaries
        massive_feed: Optional MassiveDataFeed instance
        current_prices: Optional dict of current prices by symbol
    
    Returns:
        PortfolioGreeks object
    """
    aggregator = PortfolioGreeksAggregator(massive_feed=massive_feed)
    return aggregator.aggregate_greeks(positions=positions, current_prices=current_prices)

