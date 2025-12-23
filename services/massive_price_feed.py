"""
Massive (Polygon.io) Price Data Feed
Fetches historical price bars (OHLCV) from Massive API
Supports 1-minute bars with aggregation to daily bars
"""
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
import requests
import os
import pandas as pd
import time
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class MassivePriceFeed:
    """
    Massive (formerly Polygon.io) Price Data Feed
    
    Features:
    - 1-minute bar data
    - Aggregation to daily bars
    - Historical data with point-in-time accuracy
    - Caching for performance
    """
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[Path] = None):
        """
        Initialize Massive price feed
        
        Args:
            api_key: Massive API key (defaults to MASSIVE_API_KEY or POLYGON_API_KEY env var)
            cache_dir: Directory to cache historical data (defaults to data/price_cache)
        """
        # Support both MASSIVE_API_KEY and POLYGON_API_KEY
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = (
                os.getenv('MASSIVE_API_KEY') or 
                os.getenv('POLYGON_API_KEY') or
                ''
            )
            # Try Config if env vars not set
            if not self.api_key:
                try:
                    from config import Config
                    self.api_key = Config.MASSIVE_API_KEY or Config.POLYGON_API_KEY or ''
                except:
                    pass
        
        if not self.api_key:
            logger.warning("MASSIVE_API_KEY/POLYGON_API_KEY not set. Massive price feed will be disabled.")
        
        self.base_url = "https://api.polygon.io"
        self.cache_dir = cache_dir or Path('data/price_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting (Polygon free tier: 5 requests/minute, paid: higher limits)
        self.last_request_time = 0.0
        self.min_request_interval = 0.2  # 5 requests per second max (conservative)
        
    def is_available(self) -> bool:
        """Check if Massive API is available"""
        return bool(self.api_key)
    
    def _rate_limit(self):
        """Rate limit requests to avoid exceeding API limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make API request with error handling and rate limiting
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            
        Returns:
            Response JSON or None if error
        """
        if not self.is_available():
            logger.error("Massive API key not configured")
            return None
        
        self._rate_limit()
        
        if params is None:
            params = {}
        
        params['apiKey'] = self.api_key
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK':
                return data
            elif data.get('status') == 'ERROR':
                logger.error(f"Massive API error: {data.get('error', 'Unknown error')}")
                return None
            else:
                return data
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to Massive API: {e}")
            return None
    
    def get_1minute_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 50000
    ) -> pd.DataFrame:
        """
        Get 1-minute bars from Massive API
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            limit: Maximum number of bars to return
            
        Returns:
            DataFrame with OHLCV data
        """
        if not self.is_available():
            logger.error("Massive API not available")
            return pd.DataFrame()
        
        # Check cache first
        cache_key = f"{symbol}_1min_{start_date.date()}_{end_date.date()}"
        cached = self._load_cache(cache_key)
        if cached is not None:
            logger.debug(f"Loaded cached 1-minute bars for {symbol}")
            return cached
        
        all_bars = []
        current_start = start_date
        
        try:
            while current_start < end_date:
                # Massive API aggregates endpoint for 1-minute bars
                endpoint = f"/v2/aggs/ticker/{symbol.upper()}/range/1/minute/{int(current_start.timestamp() * 1000)}/{int(end_date.timestamp() * 1000)}"
                
                params = {
                    'limit': min(50000, limit),  # Massive allows up to 50k per request
                    'sort': 'asc'
                }
                
                data = self._make_request(endpoint, params)
                
                if data and data.get('results'):
                    bars = data['results']
                    all_bars.extend(bars)
                    
                    # If we got less than requested, we've reached the end
                    if len(bars) < params['limit']:
                        break
                    
                    # Move start time forward
                    last_timestamp = bars[-1]['t'] / 1000  # Convert from milliseconds
                    current_start = datetime.fromtimestamp(last_timestamp) + timedelta(minutes=1)
                else:
                    break
                
                # Safety check
                if len(all_bars) >= limit:
                    break
            
            if not all_bars:
                logger.warning(f"No 1-minute bars found for {symbol} from {start_date} to {end_date}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(all_bars)
            df['timestamp'] = pd.to_datetime(df['t'], unit='ms', utc=True)
            df = df.rename(columns={
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume',
                'vw': 'volume_weighted_price'
            })
            
            # Select and order columns
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Cache the result
            self._save_cache(cache_key, df)
            
            logger.info(f"Retrieved {len(df)} 1-minute bars for {symbol} from Massive")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching 1-minute bars for {symbol} from Massive: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return pd.DataFrame()
    
    def get_daily_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        use_1min_aggregation: bool = True
    ) -> pd.DataFrame:
        """
        Get daily bars from Massive API
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            use_1min_aggregation: If True, get 1-minute bars and aggregate to daily
            
        Returns:
            DataFrame with daily OHLCV data
        """
        if not self.is_available():
            logger.error("Massive API not available")
            return pd.DataFrame()
        
        if use_1min_aggregation:
            # Get 1-minute bars and aggregate to daily
            logger.debug(f"Getting 1-minute bars for {symbol} and aggregating to daily")
            minute_bars = self.get_1minute_bars(symbol, start_date, end_date)
            
            if minute_bars.empty:
                return pd.DataFrame()
            
            # Aggregate to daily bars
            minute_bars['date'] = minute_bars['timestamp'].dt.date
            daily_bars = minute_bars.groupby('date').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).reset_index()
            
            daily_bars['timestamp'] = pd.to_datetime(daily_bars['date'])
            daily_bars = daily_bars[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            daily_bars = daily_bars.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Aggregated {len(minute_bars)} 1-minute bars to {len(daily_bars)} daily bars for {symbol}")
            return daily_bars
        else:
            # Use Massive's daily aggregates endpoint directly
            cache_key = f"{symbol}_daily_{start_date.date()}_{end_date.date()}"
            cached = self._load_cache(cache_key)
            if cached is not None:
                logger.debug(f"Loaded cached daily bars for {symbol}")
                return cached
            
            try:
                endpoint = f"/v2/aggs/ticker/{symbol.upper()}/range/1/day/{int(start_date.timestamp() * 1000)}/{int(end_date.timestamp() * 1000)}"
                
                params = {
                    'limit': 50000,
                    'sort': 'asc'
                }
                
                data = self._make_request(endpoint, params)
                
                if not data or not data.get('results'):
                    logger.warning(f"No daily bars found for {symbol} from {start_date} to {end_date}")
                    return pd.DataFrame()
                
                bars = data['results']
                
                # Convert to DataFrame
                df = pd.DataFrame(bars)
                df['timestamp'] = pd.to_datetime(df['t'], unit='ms', utc=True)
                df = df.rename(columns={
                    'o': 'open',
                    'h': 'high',
                    'l': 'low',
                    'c': 'close',
                    'v': 'volume',
                    'vw': 'volume_weighted_price'
                })
                
                # Select and order columns
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                # Cache the result
                self._save_cache(cache_key, df)
                
                logger.info(f"Retrieved {len(df)} daily bars for {symbol} from Massive")
                return df
                
            except Exception as e:
                logger.error(f"Error fetching daily bars for {symbol} from Massive: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                return pd.DataFrame()
    
    def _load_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Load cached data"""
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        if cache_file.exists():
            try:
                df = pd.read_parquet(cache_file)
                logger.debug(f"Loaded cached data from {cache_file}")
                return df
            except Exception as e:
                logger.debug(f"Error loading cache: {e}")
        return None
    
    def _save_cache(self, cache_key: str, df: pd.DataFrame):
        """Save data to cache"""
        if df.empty:
            return
        
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        try:
            df.to_parquet(cache_file, index=False)
            logger.debug(f"Cached data to {cache_file}")
        except Exception as e:
            logger.debug(f"Error saving cache: {e}")
