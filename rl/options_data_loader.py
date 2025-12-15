"""
Options Data Loader for RL Training
Merges stock data with options data from database for RL training
"""
import logging
import pandas as pd
import numpy as np
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from services.massive_data_feed import MassiveDataFeed
from services.iv_calculator import IVCalculator
from config import Config

logger = logging.getLogger(__name__)

class OptionsDataLoader:
    """
    Loads and merges stock + options data for RL training
    
    Features:
    - Merges stock OHLCV with options chain data
    - Extracts Greeks for ATM options
    - Calculates IV metrics from historical data
    - Adds volatility regime features
    - Provides point-in-time accuracy
    """
    
    def __init__(self, massive_feed: Optional[MassiveDataFeed] = None):
        """
        Initialize options data loader
        
        Args:
            massive_feed: MassiveDataFeed instance or None to create new
        """
        self.feed = massive_feed or MassiveDataFeed(
            api_key=Config.MASSIVE_API_KEY,
            base_url=Config.MASSIVE_BASE_URL
        )
        self.iv_calculator = IVCalculator()
        self.db_path = Path('data/options_history.db')
    
    def load_training_data(
        self,
        symbol: str,
        stock_data: pd.DataFrame,
        target_dte: int = 7,  # Target days to expiration (0-30 DTE)
        use_atm: bool = True
    ) -> pd.DataFrame:
        """
        Merge stock data with options data for RL training
        
        Args:
            symbol: Trading symbol
            stock_data: DataFrame with OHLCV data (indexed by date)
            target_dte: Target days to expiration for option selection
            use_atm: Whether to use ATM options or closest to target DTE
            
        Returns:
            DataFrame with stock + options features
        """
        logger.info(f"Loading options data for {symbol}...")
        
        if stock_data.empty:
            logger.warning(f"Empty stock data for {symbol}")
            return stock_data
        
        # Ensure date index
        if not isinstance(stock_data.index, pd.DatetimeIndex):
            if 'date' in stock_data.columns:
                stock_data['date'] = pd.to_datetime(stock_data['date'])
                stock_data = stock_data.set_index('date')
            else:
                stock_data.index = pd.date_range(start='2024-01-01', periods=len(stock_data), freq='D')
        
        # Initialize options features columns
        options_features = pd.DataFrame(index=stock_data.index)
        
        # Load options data for each date
        dates_processed = 0
        dates_with_data = 0
        
        for date in stock_data.index:
            date_str = date.strftime('%Y-%m-%d')
            dates_processed += 1
            
            try:
                # Get options chain for this date
                chain = self._get_chain_from_db(symbol, date_str)
                
                if not chain:
                    # Try API if not in DB
                    chain = self.feed.get_options_chain(symbol, date=date_str)
                
                if chain:
                    # Get ATM option or closest to target DTE
                    option_data = self._select_option_for_training(
                        chain,
                        stock_data.loc[date, 'close'],
                        target_dte,
                        use_atm
                    )
                    
                    if option_data:
                        # Extract features
                        options_features.loc[date, 'delta'] = option_data.get('delta', 0.0)
                        options_features.loc[date, 'gamma'] = option_data.get('gamma', 0.0)
                        options_features.loc[date, 'theta'] = option_data.get('theta', 0.0)
                        options_features.loc[date, 'vega'] = option_data.get('vega', 0.0)
                        options_features.loc[date, 'implied_volatility'] = option_data.get('implied_volatility', 0.0) / 100.0  # Convert from %
                        options_features.loc[date, 'option_price'] = option_data.get('last', 0.0)
                        options_features.loc[date, 'strike'] = option_data.get('strike', 0.0)
                        options_features.loc[date, 'expiration_date'] = option_data.get('expiration_date', '')
                        options_features.loc[date, 'dte'] = self._calculate_dte(date_str, option_data.get('expiration_date', ''))
                        options_features.loc[date, 'open_interest'] = option_data.get('open_interest', 0)
                        options_features.loc[date, 'option_volume'] = option_data.get('volume', 0)  # Rename to avoid conflict
                        options_features.loc[date, 'bid_ask_spread'] = (
                            (option_data.get('ask', 0) - option_data.get('bid', 0)) / 
                            option_data.get('last', 1) if option_data.get('last', 0) > 0 else 0.0
                        )
                        
                        dates_with_data += 1
                    else:
                        # No suitable option found
                        self._fill_defaults(options_features, date)
                else:
                    # No chain data
                    self._fill_defaults(options_features, date)
                
            except Exception as e:
                logger.debug(f"Error loading options for {symbol} on {date_str}: {e}")
                self._fill_defaults(options_features, date)
        
        logger.info(f"Loaded options data: {dates_with_data}/{dates_processed} dates with data")
        
        # Calculate IV metrics from historical data
        iv_metrics = self._calculate_iv_metrics(symbol, stock_data.index, options_features)
        
        # Merge all features
        merged_data = stock_data.copy()
        merged_data = pd.concat([merged_data, options_features, iv_metrics], axis=1)
        
        # Forward fill missing values (for weekends/holidays)
        # Use ffill() for pandas >= 2.0 compatibility
        merged_data = merged_data.ffill().fillna(0)
        
        return merged_data
    
    def _get_chain_from_db(self, symbol: str, date: str) -> List[Dict]:
        """Get options chain from database"""
        try:
            if not self.db_path.exists():
                return []
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT expiration_date, strike, option_type, bid, ask, last,
                       volume, open_interest, implied_volatility, delta, gamma, theta, vega, underlying_price
                FROM options_chains
                WHERE symbol = ? AND date = ?
                ORDER BY expiration_date, strike
            """, (symbol, date))
            
            rows = cursor.fetchall()
            conn.close()
            
            contracts = []
            for row in rows:
                contracts.append({
                    'expiration_date': row[0],
                    'strike': row[1],
                    'option_type': row[2],
                    'bid': row[3] or 0.0,
                    'ask': row[4] or 0.0,
                    'last': row[5] or 0.0,
                    'volume': row[6] or 0,
                    'open_interest': row[7] or 0,
                    'implied_volatility': row[8] or 0.0,
                    'delta': row[9] or 0.0,
                    'gamma': row[10] or 0.0,
                    'theta': row[11] or 0.0,
                    'vega': row[12] or 0.0,
                    'underlying_price': row[13] or 0.0
                })
            
            return contracts
            
        except Exception as e:
            logger.debug(f"Error reading from database: {e}")
            return []
    
    def _select_option_for_training(
        self,
        chain: List[Dict],
        underlying_price: float,
        target_dte: int,
        use_atm: bool
    ) -> Optional[Dict]:
        """
        Select best option for RL training
        
        Args:
            chain: Options chain
            underlying_price: Current underlying price
            target_dte: Target days to expiration
            use_atm: Use ATM or closest to target DTE
            
        Returns:
            Selected option contract
        """
        if not chain:
            return None
        
        # Filter by call options (for now, can extend to puts)
        calls = [c for c in chain if c.get('option_type', '').lower() == 'call']
        
        if not calls:
            return None
        
        # Calculate DTE for each option
        today = datetime.now()
        for option in calls:
            try:
                exp_date = datetime.strptime(option.get('expiration_date', ''), '%Y-%m-%d')
                dte = (exp_date - today).days
                option['dte'] = max(0, dte)
            except:
                option['dte'] = 999
        
        if use_atm:
            # Find ATM option (closest strike to underlying)
            atm_option = min(
                calls,
                key=lambda x: abs(x.get('strike', 0) - underlying_price)
            )
            return atm_option
        else:
            # Find option closest to target DTE
            target_option = min(
                calls,
                key=lambda x: abs(x.get('dte', 999) - target_dte)
            )
            return target_option
    
    def _calculate_dte(self, date_str: str, expiration_date: str) -> int:
        """Calculate days to expiration"""
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            exp = datetime.strptime(expiration_date, '%Y-%m-%d')
            return max(0, (exp - date).days)
        except:
            return 0
    
    def _fill_defaults(self, df: pd.DataFrame, date: pd.Timestamp):
        """Fill default values when options data not available"""
        defaults = {
            'delta': 0.5,  # Neutral delta
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0,
            'implied_volatility': 0.2,  # 20% default IV
            'option_price': 0.0,
            'strike': 0.0,
            'expiration_date': '',
            'dte': 0,
            'open_interest': 0,
            'option_volume': 0,  # Rename to avoid conflict with stock volume
            'bid_ask_spread': 0.05  # 5% default spread
        }
        
        for key, value in defaults.items():
            if key not in df.columns:
                df[key] = np.nan
            df.loc[date, key] = value
    
    def _calculate_iv_metrics(
        self,
        symbol: str,
        dates: pd.DatetimeIndex,
        options_features: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate IV Rank and IV Percentile from historical data
        
        Args:
            symbol: Trading symbol
            dates: Date index
            options_features: DataFrame with IV data
            
        Returns:
            DataFrame with IV metrics
        """
        iv_metrics = pd.DataFrame(index=dates)
        iv_metrics['iv_rank'] = 50.0
        iv_metrics['iv_percentile'] = 50.0
        iv_metrics['iv_mean'] = 0.2
        iv_metrics['iv_std'] = 0.05
        
        try:
            # Get historical IV data
            if self.db_path.exists():
                conn = sqlite3.connect(str(self.db_path))
                
                # Get IV history for this symbol
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT date, implied_volatility
                    FROM options_chains
                    WHERE symbol = ? AND implied_volatility > 0
                    ORDER BY date
                """, (symbol,))
                
                iv_history = cursor.fetchall()
                conn.close()
                
                if iv_history:
                    # Build IV history series
                    iv_series = pd.Series(
                        [iv / 100.0 for _, iv in iv_history],  # Convert from %
                        index=[pd.to_datetime(date) for date, _ in iv_history]
                    )
                    
                    # Calculate rolling metrics
                    for date in dates:
                        # Get IV for this date
                        current_iv = options_features.loc[date, 'implied_volatility'] if date in options_features.index else 0.2
                        
                        if current_iv > 0:
                            # Get historical IV up to this date
                            historical_iv = iv_series[iv_series.index <= date]
                            
                            if len(historical_iv) > 20:  # Need enough history
                                # Calculate IV Rank and Percentile
                                iv_rank = self.iv_calculator.calculate_iv_rank(
                                    symbol,
                                    current_iv,
                                    historical_iv.tolist()
                                )
                                iv_percentile = self.iv_calculator.calculate_iv_percentile(
                                    symbol,
                                    current_iv,
                                    historical_iv.tolist()
                                )
                                
                                iv_metrics.loc[date, 'iv_rank'] = iv_rank
                                iv_metrics.loc[date, 'iv_percentile'] = iv_percentile
                                iv_metrics.loc[date, 'iv_mean'] = historical_iv.mean()
                                iv_metrics.loc[date, 'iv_std'] = historical_iv.std()
                                
                                # Update IV calculator history
                                self.iv_calculator.update_iv_history(symbol, current_iv, date)
        
        except Exception as e:
            logger.debug(f"Error calculating IV metrics: {e}")
        
        return iv_metrics

