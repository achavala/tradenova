"""
UVaR (Ultra-Short VaR) Calculator
Calculates portfolio tail risk using historical simulation for 1-3 day horizons
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from alpaca_client import AlpacaClient
from config import Config

logger = logging.getLogger(__name__)

class UVaRCalculator:
    """
    Ultra-Short VaR Calculator
    
    Uses historical simulation to estimate portfolio tail risk over 1-3 day horizons
    at 99% confidence level.
    
    Methodology:
    - Historical simulation (no Monte Carlo)
    - 1-3 day horizons
    - 99% confidence
    - Rolling window (60-90 days)
    """
    
    def __init__(
        self,
        alpaca_client: Optional[AlpacaClient] = None,
        lookback_days: int = 90,
        confidence_level: float = 0.99
    ):
        """
        Initialize UVaR calculator
        
        Args:
            alpaca_client: Alpaca API client for historical data
            lookback_days: Number of days for historical simulation (default: 90)
            confidence_level: Confidence level for VaR (default: 0.99 = 99%)
        """
        self.client = alpaca_client
        self.lookback_days = lookback_days
        self.confidence_level = confidence_level
        
        # Cache for historical returns
        self._returns_cache: Dict[str, pd.Series] = {}
        self._cache_date = None
    
    def calculate_uvar(
        self,
        positions: List[Dict],
        horizon_days: int = 1,
        current_prices: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Calculate UVaR for portfolio
        
        Args:
            positions: List of position dicts with:
                - symbol: Stock symbol
                - qty: Quantity (positive for long, negative for short)
                - entry_price: Entry price
                - current_price: Current price (optional)
            horizon_days: VaR horizon in days (1, 2, or 3)
            current_prices: Optional dict of current prices (if None, fetches)
            
        Returns:
            Dictionary with:
            - uvar: UVaR value (dollar amount)
            - uvar_pct: UVaR as percentage of portfolio value
            - portfolio_value: Current portfolio value
            - worst_case_loss: Worst case loss from historical simulation
        """
        if not positions:
            return {
                'uvar': 0.0,
                'uvar_pct': 0.0,
                'portfolio_value': 0.0,
                'worst_case_loss': 0.0
            }
        
        # Get current prices if not provided
        if current_prices is None:
            current_prices = self._get_current_prices([p['symbol'] for p in positions])
        
        # Calculate portfolio value
        portfolio_value = sum(
            abs(p.get('current_price', p.get('entry_price', 0)) * p.get('qty', 0))
            for p in positions
        )
        
        if portfolio_value == 0:
            return {
                'uvar': 0.0,
                'uvar_pct': 0.0,
                'portfolio_value': 0.0,
                'worst_case_loss': 0.0
            }
        
        # Get historical returns for all symbols
        symbols = list(set(p['symbol'] for p in positions))
        returns_data = self._get_historical_returns(symbols, horizon_days)
        
        if not returns_data:
            logger.warning("Insufficient historical data for UVaR calculation")
            return {
                'uvar': 0.0,
                'uvar_pct': 0.0,
                'portfolio_value': portfolio_value,
                'worst_case_loss': 0.0
            }
        
        # Calculate portfolio P&L for each historical scenario
        portfolio_pnls = []
        
        for date_idx in range(len(returns_data[list(returns_data.keys())[0]])):
            scenario_pnl = 0.0
            
            for position in positions:
                symbol = position['symbol']
                qty = position.get('qty', 0)
                current_price = position.get('current_price', position.get('entry_price', 0))
                
                if symbol not in returns_data:
                    continue
                
                # Get return for this scenario
                if date_idx < len(returns_data[symbol]):
                    return_pct = returns_data[symbol].iloc[date_idx]
                    
                    # Calculate P&L for this position in this scenario
                    position_value = abs(current_price * qty)
                    scenario_pnl += position_value * return_pct * (1 if qty > 0 else -1)
            
            portfolio_pnls.append(scenario_pnl)
        
        if not portfolio_pnls:
            return {
                'uvar': 0.0,
                'uvar_pct': 0.0,
                'portfolio_value': portfolio_value,
                'worst_case_loss': 0.0
            }
        
        # Calculate VaR at confidence level
        portfolio_pnls = np.array(portfolio_pnls)
        
        # Sort losses (negative P&L)
        losses = -portfolio_pnls  # Convert to losses (positive = loss)
        losses = np.sort(losses)
        
        # Calculate percentile
        percentile_idx = int((1 - self.confidence_level) * len(losses))
        percentile_idx = max(0, min(percentile_idx, len(losses) - 1))
        
        uvar = losses[percentile_idx]
        worst_case_loss = losses[-1] if len(losses) > 0 else 0.0
        
        uvar_pct = (uvar / portfolio_value) * 100 if portfolio_value > 0 else 0.0
        
        return {
            'uvar': uvar,
            'uvar_pct': uvar_pct,
            'portfolio_value': portfolio_value,
            'worst_case_loss': worst_case_loss,
            'horizon_days': horizon_days,
            'confidence_level': self.confidence_level,
            'scenarios': len(portfolio_pnls)
        }
    
    def check_uvar_breach(
        self,
        positions: List[Dict],
        max_uvar_pct: float = 5.0,
        horizon_days: int = 1
    ) -> Tuple[bool, str, Dict]:
        """
        Check if UVaR exceeds threshold
        
        Args:
            positions: List of position dicts
            max_uvar_pct: Maximum UVaR as percentage of portfolio (default: 5%)
            horizon_days: VaR horizon in days
            
        Returns:
            Tuple of (is_breach, reason, uvar_result)
        """
        uvar_result = self.calculate_uvar(positions, horizon_days)
        
        if uvar_result['uvar_pct'] > max_uvar_pct:
            return (
                True,
                f"UVaR breach: {uvar_result['uvar_pct']:.2f}% > {max_uvar_pct}% threshold",
                uvar_result
            )
        
        return (False, "UVaR within limits", uvar_result)
    
    def _get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for symbols"""
        prices = {}
        
        if not self.client:
            logger.warning("No Alpaca client available for UVaR")
            return prices
        
        for symbol in symbols:
            try:
                # Use get_latest_price method
                price = self.client.get_latest_price(symbol)
                if price:
                    prices[symbol] = price
            except Exception as e:
                logger.warning(f"Could not get price for {symbol}: {e}")
        
        return prices
    
    def _get_historical_returns(
        self,
        symbols: List[str],
        horizon_days: int
    ) -> Dict[str, pd.Series]:
        """
        Get historical returns for symbols over specified horizon
        
        Args:
            symbols: List of stock symbols
            horizon_days: Return horizon (1, 2, or 3 days)
            
        Returns:
            Dictionary mapping symbol -> Series of returns
        """
        returns_data = {}
        
        if not self.client:
            logger.warning("No Alpaca client available for historical data")
            return returns_data
        
        # Check cache
        today = datetime.now().date()
        if self._cache_date != today:
            self._returns_cache = {}
            self._cache_date = today
        
        for symbol in symbols:
            try:
                # Check cache first
                if symbol in self._returns_cache:
                    returns = self._returns_cache[symbol]
                else:
                    # Fetch historical bars using get_historical_bars
                    from alpaca_trade_api.rest import TimeFrame
                    
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=self.lookback_days + horizon_days)
                    
                    df = self.client.get_historical_bars(
                        symbol,
                        TimeFrame.Day,
                        start_date,
                        end_date
                    )
                    
                    if df.empty or len(df) < horizon_days + 1:
                        logger.warning(f"Insufficient data for {symbol}: {len(df)} bars")
                        continue
                    
                    # Ensure 'close' column exists (Alpaca returns different column names)
                    if 'close' not in df.columns:
                        if 'c' in df.columns:
                            df['close'] = df['c']
                        else:
                            logger.warning(f"No close price column found for {symbol}")
                            continue
                    
                    # Calculate returns over horizon
                    if horizon_days == 1:
                        returns = df['close'].pct_change(periods=1).dropna()
                    elif horizon_days == 2:
                        returns = df['close'].pct_change(periods=2).dropna()
                    elif horizon_days == 3:
                        returns = df['close'].pct_change(periods=3).dropna()
                    else:
                        # For other horizons, use forward-looking returns
                        returns = df['close'].pct_change(periods=horizon_days).dropna()
                    
                    # Cache returns
                    self._returns_cache[symbol] = returns
                
                returns_data[symbol] = returns
                
            except Exception as e:
                logger.error(f"Error getting historical returns for {symbol}: {e}")
                continue
        
        return returns_data
    
    def calculate_incremental_uvar(
        self,
        current_positions: List[Dict],
        new_position: Dict,
        horizon_days: int = 1
    ) -> Dict[str, float]:
        """
        Calculate incremental UVaR impact of adding a new position
        
        Args:
            current_positions: Current portfolio positions
            new_position: New position to add
            horizon_days: VaR horizon
            
        Returns:
            Dictionary with incremental UVaR impact
        """
        # Calculate UVaR without new position
        uvar_before = self.calculate_uvar(current_positions, horizon_days)
        
        # Calculate UVaR with new position
        positions_with_new = current_positions + [new_position]
        uvar_after = self.calculate_uvar(positions_with_new, horizon_days)
        
        return {
            'uvar_before': uvar_before['uvar'],
            'uvar_after': uvar_after['uvar'],
            'incremental_uvar': uvar_after['uvar'] - uvar_before['uvar'],
            'incremental_uvar_pct': uvar_after['uvar_pct'] - uvar_before['uvar_pct'],
            'uvar_before_pct': uvar_before['uvar_pct'],
            'uvar_after_pct': uvar_after['uvar_pct']
        }

