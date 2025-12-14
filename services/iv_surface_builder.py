"""
IV Surface Builder
Constructs implied volatility surfaces from Massive API data
Essential for options pricing, Greeks calculation, and RL training
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from scipy.interpolate import griddata, RBFInterpolator
from scipy.optimize import minimize

from services.massive_data_feed import MassiveDataFeed
from config import Config

logger = logging.getLogger(__name__)

class IVSurfaceBuilder:
    """
    Builds implied volatility surfaces from options data
    
    Features:
    - IV surface interpolation
    - Strike/expiry surface construction
    - Volatility smile extraction
    - Term structure analysis
    - Surface visualization data
    """
    
    def __init__(self, massive_feed: Optional[MassiveDataFeed] = None):
        """
        Initialize IV surface builder
        
        Args:
            massive_feed: MassiveDataFeed instance or None to create new
        """
        self.feed = massive_feed or MassiveDataFeed(
            api_key=Config.MASSIVE_API_KEY,
            base_url=Config.MASSIVE_BASE_URL
        )
    
    def build_iv_surface(
        self,
        symbol: str,
        date: str,
        expiration_date: Optional[str] = None,
        method: str = 'rbf'
    ) -> Dict:
        """
        Build IV surface for a symbol at a specific date
        
        Args:
            symbol: Underlying symbol
            date: Date for surface (YYYY-MM-DD)
            expiration_date: Specific expiration or None for all
            method: Interpolation method ('rbf', 'linear', 'cubic')
            
        Returns:
            Dictionary with:
            - strikes: Array of strike prices
            - expirations: Array of expiration dates
            - iv_surface: 2D array of IV values
            - underlying_price: Current underlying price
            - metadata: Surface metadata
        """
        # Get options chain
        chain = self.feed.get_options_chain(symbol, expiration_date=expiration_date, date=date)
        
        if not chain:
            logger.warning(f"No options data for {symbol} on {date}")
            return self._empty_surface()
        
        # Extract data points
        strikes = []
        expirations = []
        ivs = []
        underlying_price = chain[0].get('underlying_price', 0) if chain else 0
        
        for contract in chain:
            strike = contract.get('strike', 0)
            exp_date = contract.get('expiration_date', '')
            iv = contract.get('implied_volatility', 0)
            
            if strike > 0 and exp_date and iv > 0:
                # Convert expiration to days to expiration
                try:
                    exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
                    date_dt = datetime.strptime(date, '%Y-%m-%d')
                    dte = (exp_dt - date_dt).days
                    
                    if dte > 0:  # Only include future expirations
                        strikes.append(strike)
                        expirations.append(dte)
                        ivs.append(iv / 100.0)  # Convert from percentage
                except ValueError:
                    continue
        
        if not strikes:
            return self._empty_surface()
        
        # Build surface using interpolation
        surface = self._interpolate_surface(
            np.array(strikes),
            np.array(expirations),
            np.array(ivs),
            underlying_price,
            method=method
        )
        
        return {
            'symbol': symbol,
            'date': date,
            'underlying_price': underlying_price,
            'strikes': surface['strikes'],
            'expirations': surface['expirations'],
            'iv_surface': surface['iv_surface'],
            'data_points': len(strikes),
            'method': method
        }
    
    def _interpolate_surface(
        self,
        strikes: np.ndarray,
        dtes: np.ndarray,
        ivs: np.ndarray,
        underlying_price: float,
        method: str = 'rbf'
    ) -> Dict:
        """
        Interpolate IV surface from data points
        
        Args:
            strikes: Strike prices
            dtes: Days to expiration
            ivs: Implied volatilities
            underlying_price: Current underlying price
            method: Interpolation method
            
        Returns:
            Dictionary with interpolated surface
        """
        # Create grid
        strike_min = max(strikes.min() * 0.5, underlying_price * 0.3)
        strike_max = min(strikes.max() * 1.5, underlying_price * 2.0)
        dte_min = max(1, int(dtes.min()))
        dte_max = int(dtes.max())
        
        # Generate grid
        strike_grid = np.linspace(strike_min, strike_max, 50)
        dte_grid = np.linspace(dte_min, dte_max, 30)
        strike_mesh, dte_mesh = np.meshgrid(strike_grid, dte_grid)
        
        # Interpolate
        if method == 'rbf':
            try:
                # Use RBF interpolation for smooth surface
                rbf = RBFInterpolator(
                    np.column_stack([strikes, dtes]),
                    ivs,
                    kernel='thin_plate_spline',
                    smoothing=0.1
                )
                points = np.column_stack([strike_mesh.ravel(), dte_mesh.ravel()])
                iv_surface = rbf(points).reshape(strike_mesh.shape)
            except Exception as e:
                logger.warning(f"RBF interpolation failed: {e}, using linear")
                method = 'linear'
        
        if method == 'linear' or method == 'cubic':
            # Use griddata for linear/cubic interpolation
            points = np.column_stack([strikes, dtes])
            grid_points = np.column_stack([strike_mesh.ravel(), dte_mesh.ravel()])
            iv_surface = griddata(
                points,
                ivs,
                grid_points,
                method=method,
                fill_value=np.nanmean(ivs)  # Fill NaN with mean IV
            ).reshape(strike_mesh.shape)
        
        # Clip to reasonable values
        iv_surface = np.clip(iv_surface, 0.01, 5.0)  # 1% to 500% IV
        
        return {
            'strikes': strike_grid,
            'expirations': dte_grid,
            'iv_surface': iv_surface
        }
    
    def extract_volatility_smile(
        self,
        symbol: str,
        date: str,
        expiration_date: str
    ) -> Dict:
        """
        Extract volatility smile for a specific expiration
        
        Args:
            symbol: Underlying symbol
            date: Date (YYYY-MM-DD)
            expiration_date: Expiration date (YYYY-MM-DD)
            
        Returns:
            Dictionary with smile data
        """
        chain = self.feed.get_options_chain(symbol, expiration_date=expiration_date, date=date)
        
        if not chain:
            return {'strikes': [], 'ivs': [], 'underlying_price': 0}
        
        underlying_price = chain[0].get('underlying_price', 0) if chain else 0
        
        strikes = []
        ivs = []
        
        for contract in chain:
            strike = contract.get('strike', 0)
            iv = contract.get('implied_volatility', 0)
            
            if strike > 0 and iv > 0:
                strikes.append(strike)
                ivs.append(iv / 100.0)
        
        # Sort by strike
        sorted_data = sorted(zip(strikes, ivs))
        strikes = [s for s, _ in sorted_data]
        ivs = [iv for _, iv in sorted_data]
        
        return {
            'strikes': strikes,
            'ivs': ivs,
            'underlying_price': underlying_price,
            'expiration_date': expiration_date
        }
    
    def get_term_structure(
        self,
        symbol: str,
        date: str,
        strike: Optional[float] = None
    ) -> Dict:
        """
        Get IV term structure
        
        Args:
            symbol: Underlying symbol
            date: Date (YYYY-MM-DD)
            strike: Strike price or None for ATM
            
        Returns:
            Dictionary with term structure data
        """
        chain = self.feed.get_options_chain(symbol, date=date)
        
        if not chain:
            return {'expirations': [], 'ivs': [], 'dtes': []}
        
        underlying_price = chain[0].get('underlying_price', 0) if chain else 0
        
        # If no strike specified, use ATM
        if strike is None:
            strike = underlying_price
        
        # Find closest strike for each expiration
        expirations = {}
        
        for contract in chain:
            exp_date = contract.get('expiration_date', '')
            contract_strike = contract.get('strike', 0)
            iv = contract.get('implied_volatility', 0)
            
            if exp_date and iv > 0:
                # Calculate DTE
                try:
                    exp_dt = datetime.strptime(exp_date, '%Y-%m-%d')
                    date_dt = datetime.strptime(date, '%Y-%m-%d')
                    dte = (exp_dt - date_dt).days
                    
                    if dte > 0:
                        # Find closest strike
                        if exp_date not in expirations:
                            expirations[exp_date] = {
                                'dte': dte,
                                'strikes': [],
                                'ivs': []
                            }
                        
                        expirations[exp_date]['strikes'].append(contract_strike)
                        expirations[exp_date]['ivs'].append(iv / 100.0)
                except ValueError:
                    continue
        
        # For each expiration, find IV at target strike
        term_data = []
        for exp_date, data in sorted(expirations.items(), key=lambda x: x[1]['dte']):
            strikes = data['strikes']
            ivs = data['ivs']
            
            # Interpolate IV at target strike
            if len(strikes) > 1:
                iv_at_strike = np.interp(strike, strikes, ivs)
            elif len(strikes) == 1:
                iv_at_strike = ivs[0]
            else:
                continue
            
            term_data.append({
                'expiration_date': exp_date,
                'dte': data['dte'],
                'iv': iv_at_strike
            })
        
        return {
            'expirations': [d['expiration_date'] for d in term_data],
            'dtes': [d['dte'] for d in term_data],
            'ivs': [d['iv'] for d in term_data],
            'strike': strike
        }
    
    def _empty_surface(self) -> Dict:
        """Return empty surface structure"""
        return {
            'symbol': '',
            'date': '',
            'underlying_price': 0,
            'strikes': np.array([]),
            'expirations': np.array([]),
            'iv_surface': np.array([]),
            'data_points': 0,
            'method': 'none'
        }

