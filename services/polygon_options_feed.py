"""
Polygon.io Options Data Feed
Professional options data provider for historical and real-time options chains
Provides point-in-time accuracy for backtesting and IV history
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import requests
import os
import pandas as pd
import time
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class MassiveOptionsFeed:
    """
    Massive (formerly Polygon.io) Options Data Feed
    
    Polygon.io has rebranded to Massive.com (October 2025).
    API endpoints remain compatible - both api.polygon.io and api.massive.com work.
    
    Features:
    - Historical options chain data
    - Point-in-time snapshots for backtesting
    - IV history tracking
    - Greeks data
    - Expiration dates
    - Strike prices
    """
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[Path] = None):
        """
        Initialize Massive options feed
        
        Args:
            api_key: Massive API key (defaults to MASSIVE_API_KEY or POLYGON_API_KEY env var, or Config)
            cache_dir: Directory to cache historical data (defaults to data/options_cache)
        """
        # Support both MASSIVE_API_KEY and POLYGON_API_KEY for backwards compatibility
        # Also check Config if env vars not set
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
            logger.warning("MASSIVE_API_KEY/POLYGON_API_KEY not set. Massive features will be disabled.")
        
        self.base_url = "https://api.polygon.io"
        self.cache_dir = cache_dir or Path('data/options_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting (Polygon free tier: 5 requests/minute)
        self.last_request_time = 0.0
        self.min_request_interval = 12.0  # 5 requests per minute = 12 seconds between requests
        
    def is_available(self) -> bool:
        """Check if Massive API is available"""
        return bool(self.api_key)
    
    def _rate_limit(self):
        """Rate limit requests to avoid exceeding API limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f} seconds")
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
        
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['apiKey'] = self.api_key
        
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
                logger.warning(f"Unexpected Massive API response status: {data.get('status')}")
                return data
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Massive API request failed: {e}")
            return None
    
    def get_options_chain(
        self,
        symbol: str,
        expiration_date: Optional[str] = None,
        date: Optional[str] = None,
        as_of_date: Optional[str] = None,
        strike_min: Optional[float] = None,
        strike_max: Optional[float] = None,
        current_price: Optional[float] = None
    ) -> List[Dict]:
        """
        Get options chain for a symbol with REAL prices, premiums, and Greeks
        
        Args:
            symbol: Underlying symbol (e.g., 'AAPL')
            expiration_date: Optional expiration date filter (YYYY-MM-DD)
            date: Optional date for historical snapshot (YYYY-MM-DD) - for backtesting
            as_of_date: Alias for date parameter
            strike_min: Minimum strike price (for filtering)
            strike_max: Maximum strike price (for filtering)
            current_price: Current stock price (for ATM filtering)
            
        Returns:
            List of option contracts with full data including prices, Greeks, IV
        """
        if not self.is_available():
            return []
        
        # Use date or as_of_date for point-in-time queries
        snapshot_date = date or as_of_date
        
        # For historical data, use different approach
        if snapshot_date:
            return self._get_historical_options_chain(symbol, expiration_date, snapshot_date)
        
        # For real-time data, use snapshot endpoint with filters
        try:
            # First, get current stock price if not provided
            if current_price is None:
                current_price = self._get_current_stock_price(symbol)
            
            # Use snapshot endpoint which provides REAL prices and Greeks
            endpoint = f"/v3/snapshot/options/{symbol.upper()}"
            params = {}
            
            if expiration_date:
                params['expiration_date'] = expiration_date
            
            # Add strike filters if provided
            if strike_min is not None:
                params['strike_price.gte'] = strike_min
            if strike_max is not None:
                params['strike_price.lte'] = strike_max
            
            # If no strike filters, default to reasonable range around current price
            if current_price and strike_min is None and strike_max is None:
                params['strike_price.gte'] = current_price * 0.5  # 50% below
                params['strike_price.lte'] = current_price * 1.5  # 50% above
            
            data = self._make_request(endpoint, params)
            
            if not data or data.get('status') != 'OK':
                logger.warning(f"Snapshot endpoint returned no data for {symbol}")
                return []
            
            results = data.get('results', [])
            
            if not results:
                logger.warning(f"No options found for {symbol} with filters: {params}")
                return []
            
            # Filter by expiration if specified (snapshot may not filter correctly)
            if expiration_date:
                results = [
                    r for r in results 
                    if r.get('details', {}).get('expiration_date') == expiration_date
                ]
            
            # CRITICAL: Sort by strike price to ensure consistent ordering
            # This ensures we get the exact contracts requested
            results.sort(key=lambda x: x.get('details', {}).get('strike_price', 0))
            
            # Validate data quality - log if we see suspicious values
            for contract in results[:5]:  # Check first 5
                details = contract.get('details', {})
                strike = details.get('strike_price', 0)
                day = contract.get('day', {})
                price = day.get('close', 0)
                
                # Warn if strike seems too low (penny options)
                if strike > 0 and strike < 1.0:
                    logger.warning(f"Suspicious low strike ${strike} for {symbol} - may be penny option")
                # Warn if price seems too high relative to strike
                if strike > 0 and price > strike * 0.5:
                    logger.debug(f"High premium ${price} for ${strike} strike - may be deep ITM")
            
            logger.info(f"Retrieved {len(results)} option contracts with REAL data for {symbol} from Massive")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol} from Massive: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _get_current_stock_price(self, symbol: str) -> Optional[float]:
        """Get current stock price from snapshot endpoint"""
        try:
            endpoint = f"/v3/snapshot/options/{symbol.upper()}"
            data = self._make_request(endpoint, {'limit': 1})
            if data and data.get('results'):
                underlying = data['results'][0].get('underlying_asset', {})
                price = underlying.get('price')
                if price:
                    return float(price)
        except Exception as e:
            logger.debug(f"Could not get current price for {symbol}: {e}")
        return None
    
    def _get_historical_options_chain(
        self,
        symbol: str,
        expiration_date: Optional[str],
        date: str
    ) -> List[Dict]:
        """Get historical options chain data"""
        # Try cache first
        cache_key = f"{symbol}_{date}_{expiration_date or 'all'}"
        cached = self._load_cache(cache_key)
        if cached is not None:
            logger.debug(f"Loaded cached options chain for {symbol} on {date}")
            return cached
        
        # For historical data, use contracts endpoint to get available contracts
        # Then enrich with historical quotes
        endpoint = f"/v3/reference/options/contracts"
        params = {
            'underlying_ticker': symbol.upper(),
            'limit': 1000,
            'order': 'asc',
            'sort': 'strike_price'
        }
        
        if expiration_date:
            params['expiration_date'] = expiration_date
        
        # Filter to reasonable strikes (avoid penny options)
        params['strike_price.gte'] = 1.0  # Minimum $1 strike
        
        all_contracts = []
        try:
            data = self._make_request(endpoint, params)
            if data and data.get('status') == 'OK':
                all_contracts = data.get('results', [])
        except Exception as e:
            logger.error(f"Error fetching historical contracts: {e}")
        
        # Enrich with historical quotes
        if all_contracts:
            enriched = self._enrich_with_historical_quotes(all_contracts[:50], date)  # Limit to 50 for performance
            self._save_cache(cache_key, enriched)
            return enriched
        
        return []
    
    def _enrich_with_historical_quotes(
        self,
        contracts: List[Dict],
        date: str
    ) -> List[Dict]:
        """
        Enrich contracts with historical quotes for point-in-time backtesting
        
        Args:
            contracts: List of contract dictionaries
            date: Date to get quotes for (YYYY-MM-DD)
            
        Returns:
            Enriched contracts with historical prices and Greeks
        """
        enriched = []
        
        for contract in contracts[:50]:  # Limit to avoid too many API calls
            contract_ticker = contract.get('ticker')
            if not contract_ticker:
                continue
            
            # Get historical snapshot for this contract on the date
            quote = self.get_historical_option_quote(contract_ticker, date)
            if quote:
                contract.update(quote)
            
            enriched.append(contract)
            time.sleep(0.1)  # Small delay between requests
        
        return enriched
    
    def get_historical_option_quote(
        self,
        option_ticker: str,
        date: str
    ) -> Optional[Dict]:
        """
        Get historical quote for an option on a specific date
        
        Args:
            option_ticker: Option ticker (e.g., 'O:AAPL230120C00150000')
            date: Date (YYYY-MM-DD)
            
        Returns:
            Quote data with bid, ask, last, volume, IV, Greeks
        """
        if not self.is_available():
            return None
        
        # Use Massive/Polygon's daily options aggregates endpoint
        endpoint = f"/v2/aggs/ticker/{option_ticker}/range/1/day/{date}/{date}"
        
        data = self._make_request(endpoint)
        if not data or not data.get('results'):
            return None
        
        result = data['results'][0]  # First (and should be only) result
        
        return {
            'open': result.get('o'),
            'high': result.get('h'),
            'low': result.get('l'),
            'close': result.get('c'),
            'volume': result.get('v'),
            'vwap': result.get('vw'),
            'timestamp': result.get('t')
        }
    
    def get_expiration_dates(self, symbol: str) -> List[str]:
        """
        Get available expiration dates for a symbol
        
        Args:
            symbol: Underlying symbol
            
        Returns:
            List of expiration dates (YYYY-MM-DD) sorted ascending
        """
        if not self.is_available():
            return []
        
        # Use contracts endpoint to get all available expirations
        endpoint = f"/v3/reference/options/contracts"
        params = {
            'underlying_ticker': symbol.upper(),
            'limit': 1000,
            'order': 'asc',
            'sort': 'expiration_date'
        }
        
        try:
            data = self._make_request(endpoint, params)
            if data and data.get('status') == 'OK':
                contracts = data.get('results', [])
                
                # Extract unique expiration dates
                expirations = sorted(set(
                    contract.get('expiration_date') 
                    for contract in contracts 
                    if contract.get('expiration_date')
                ))
                
                return expirations
        except Exception as e:
            logger.error(f"Error fetching expiration dates for {symbol}: {e}")
        
        return []
    
    def get_atm_options(
        self,
        symbol: str,
        expiration_date: str,
        option_type: str,
        current_price: Optional[float] = None,
        exact_strike: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Get at-the-money option for a symbol with REAL prices and Greeks
        
        Args:
            symbol: Underlying symbol
            expiration_date: Expiration date (YYYY-MM-DD)
            option_type: 'call' or 'put'
            current_price: Current stock price (if None, will fetch)
            exact_strike: If provided, get exact strike instead of finding closest ATM
            
        Returns:
            ATM option contract with real data (prices, Greeks, IV) or None
        """
        # Get current price if not provided
        if current_price is None:
            current_price = self._get_current_stock_price(symbol)
        
        if current_price is None:
            logger.warning(f"Could not determine current price for {symbol}")
            return None
        
        # If exact strike provided, query directly
        if exact_strike is not None:
            chain = self.get_options_chain(
                symbol,
                expiration_date=expiration_date,
                strike_min=exact_strike - 0.01,  # Small range to get exact strike
                strike_max=exact_strike + 0.01,
                current_price=current_price
            )
        else:
            # Get options chain with strike range around current price
            strike_range = current_price * 0.1  # 10% range for ATM selection
            chain = self.get_options_chain(
                symbol,
                expiration_date=expiration_date,
                strike_min=current_price - strike_range,
                strike_max=current_price + strike_range,
                current_price=current_price
            )
        
        if not chain:
            return None
        
        # Filter by option type (check in details.contract_type)
        filtered = []
        for c in chain:
            contract_type = c.get('details', {}).get('contract_type', '')
            if contract_type.lower() == option_type.lower():
                filtered.append(c)
        
        if not filtered:
            return None
        
        # If exact strike provided, find it
        if exact_strike is not None:
            for contract in filtered:
                strike = contract.get('details', {}).get('strike_price', 0)
                if abs(strike - exact_strike) < 0.01:  # Within 1 cent
                    return contract
            return None
        
        # Find closest strike to current price
        best_match = None
        min_diff = float('inf')
        
        for contract in filtered:
            strike = contract.get('details', {}).get('strike_price', 0)
            if strike > 0:
                diff = abs(strike - current_price)
                if diff < min_diff:
                    min_diff = diff
                    best_match = contract
        
        return best_match
    
    def get_option_by_strike(
        self,
        symbol: str,
        strike: float,
        expiration_date: str,
        option_type: str = 'call'
    ) -> Optional[Dict]:
        """
        Get EXACT option contract by strike price with REAL data
        
        Args:
            symbol: Underlying symbol
            strike: Exact strike price
            expiration_date: Expiration date (YYYY-MM-DD)
            option_type: 'call' or 'put'
            
        Returns:
            Exact option contract with real data or None
        """
        return self.get_atm_options(
            symbol,
            expiration_date,
            option_type,
            exact_strike=strike
        )
    
    def get_iv_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        expiration_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get IV history for a symbol
        
        Args:
            symbol: Underlying symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            expiration_date: Optional expiration date filter
            
        Returns:
            DataFrame with date, IV, and other metrics
        """
        if not self.is_available():
            return pd.DataFrame()
        
        # For IV history, we need to iterate through dates and get ATM IV
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        iv_data = []
        
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            
            # Skip weekends
            if date.weekday() >= 5:
                continue
            
            # Get options chain for this date
            chain = self.get_options_chain(symbol, expiration_date=expiration_date, date=date_str)
            
            if chain:
                # Get ATM option IV (if available in contract data)
                # Note: Polygon may not always include IV in contract metadata
                # In production, you might need to calculate from prices using Black-Scholes
                for contract in chain:
                    if contract.get('implied_volatility'):
                        iv_data.append({
                            'date': date_str,
                            'iv': contract.get('implied_volatility'),
                            'expiration_date': contract.get('expiration_date'),
                            'strike': contract.get('strike_price'),
                            'option_type': contract.get('contract_type')
                        })
                        break  # Just get one IV value per date for now
        
        if not iv_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(iv_data)
        return df
    
    def _load_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """Load cached options data"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.debug(f"Error loading cache {cache_key}: {e}")
        return None
    
    def _save_cache(self, cache_key: str, data: List[Dict]):
        """Save options data to cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Error saving cache {cache_key}: {e}")


# Backwards compatibility alias (Polygon.io → Massive)
PolygonOptionsFeed = MassiveOptionsFeed

