"""
Massive API Options Data Feed
Comprehensive options data collection for TradeNova
Provides historical options chains, IV surfaces, Greeks, and point-in-time data
"""
import logging
import os
import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import json
import time

logger = logging.getLogger(__name__)

class MassiveDataFeed:
    """
    Massive API client for options data
    
    Features:
    - Historical options chains (point-in-time)
    - Historical IV data
    - Real-time options quotes
    - Greeks calculation
    - IV surface construction
    - Term structure analysis
    - Skew calculation
    - Strike clustering
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.massive.com"):
        """
        Initialize Massive API client
        
        Args:
            api_key: Massive API key (defaults to MASSIVE_API_KEY env var)
            base_url: API base URL
        """
        self.api_key = api_key or os.getenv('MASSIVE_API_KEY')
        if not self.api_key:
            logger.warning("MASSIVE_API_KEY not set. Massive features will be disabled.")
        
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}' if self.api_key else '',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Data cache directory
        self.cache_dir = Path('data/options_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Database for historical data
        self.db_path = Path('data/options_history.db')
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for historical options data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Options chains table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS options_chains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                expiration_date TEXT NOT NULL,
                strike REAL NOT NULL,
                option_type TEXT NOT NULL,
                bid REAL,
                ask REAL,
                last REAL,
                volume INTEGER,
                open_interest INTEGER,
                implied_volatility REAL,
                delta REAL,
                gamma REAL,
                theta REAL,
                vega REAL,
                underlying_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date, expiration_date, strike, option_type)
            )
        ''')
        
        # IV history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iv_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                expiration_date TEXT,
                strike REAL,
                implied_volatility REAL,
                underlying_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date, expiration_date, strike)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chains_symbol_date ON options_chains(symbol, date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_iv_symbol_date ON iv_history(symbol, date)')
        
        conn.commit()
        conn.close()
        logger.info(f"Initialized options database: {self.db_path}")
    
    def is_available(self) -> bool:
        """Check if Massive API is available"""
        return self.api_key is not None
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, method: str = 'GET') -> Optional[Dict]:
        """
        Make API request with error handling and rate limiting
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            method: HTTP method
            
        Returns:
            Response JSON or None if error
        """
        if not self.is_available():
            logger.warning("Massive API key not configured")
            return None
        
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, timeout=30)
            else:
                response = self.session.request(method, url, json=params, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Massive API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"API error: {error_data}")
                except:
                    logger.error(f"HTTP {e.response.status_code}: {e.response.text[:500]}")
            else:
                logger.error(f"Request exception (no response): {type(e).__name__}: {e}")
            return None
    
    def get_options_chain(
        self,
        symbol: str,
        expiration_date: Optional[str] = None,
        date: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        Get options chain for a symbol
        
        Args:
            symbol: Underlying symbol (e.g., 'AAPL')
            expiration_date: Filter by expiration date (YYYY-MM-DD) or None for all
            date: Historical date for point-in-time data (YYYY-MM-DD) or None for current
            use_cache: Whether to use cached data if available
            
        Returns:
            List of option contracts with full data
        """
        if not self.is_available():
            return []
        
        # Check cache first
        if use_cache and date:
            cached = self._get_cached_chain(symbol, date, expiration_date)
            if cached:
                logger.debug(f"Using cached chain for {symbol} on {date}")
                return cached
        
        try:
            # Massive API endpoint for options chains
            # Adjust endpoint based on Massive API documentation
            endpoint = "v3/snapshot/options/{symbol}".format(symbol=symbol)
            
            params = {}
            if expiration_date:
                params['expiration_date'] = expiration_date
            if date:
                params['date'] = date  # Point-in-time snapshot
            
            # Handle pagination - collect all contracts
            all_contracts = []
            next_url = None
            page_count = 0
            max_pages = 100  # Safety limit
            
            while page_count < max_pages:
                # Make request
                if next_url:
                    # Use next_url for pagination (remove base URL if present)
                    pagination_endpoint = next_url.replace(self.base_url + '/', '').lstrip('/')
                    data = self._make_request(pagination_endpoint, {})
                else:
                    data = self._make_request(endpoint, params)
                
                if not data:
                    break
                
                # Parse response
                contracts = []
                if isinstance(data, dict):
                    if 'results' in data:
                        contracts = data['results']
                    elif 'data' in data:
                        contracts = data['data']
                    elif 'items' in data:
                        contracts = data['items']
                    elif 'contracts' in data:
                        contracts = data['contracts']
                    elif 'options' in data:
                        contracts = data['options']
                    else:
                        # Try to find any list-like structure
                        for key, value in data.items():
                            if isinstance(value, list):
                                contracts = value
                                logger.debug(f"Found contracts in key '{key}'")
                                break
                    
                    # Check for pagination
                    next_url = data.get('next_url')
                elif isinstance(data, list):
                    contracts = data
                else:
                    logger.warning(f"Unexpected API response type: {type(data)}")
                    break
                
                if contracts:
                    all_contracts.extend(contracts)
                    page_count += 1
                    if page_count == 1:
                        logger.debug(f"Retrieved {len(contracts)} contracts from first page")
                    else:
                        logger.debug(f"Page {page_count}: +{len(contracts)} contracts (total: {len(all_contracts)})")
                
                # Break if no more pages
                if not next_url or not contracts:
                    break
            
            contracts = all_contracts
            
            # Normalize contract data
            normalized = []
            if not contracts:
                logger.debug(f"Empty contracts list for {symbol} on {date}")
            else:
                logger.debug(f"Processing {len(contracts)} raw contracts for {symbol}")
            
            for contract in contracts:
                normalized_contract = self._normalize_contract(contract, symbol, date)
                if normalized_contract:
                    normalized.append(normalized_contract)
                else:
                    logger.debug(f"Contract normalization failed: {contract.get('strike', 'N/A')} {contract.get('expiration_date', 'N/A')}")
            
            # Cache the result
            if use_cache and date:
                self._cache_chain(symbol, date, normalized)
            
            # Store in database
            if date:
                self._store_chain_in_db(symbol, date, normalized)
            
            logger.info(f"Retrieved {len(normalized)} option contracts for {symbol}")
            return normalized
            
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {e}")
            return []
    
    def _normalize_contract(self, contract: Dict, symbol: str, date: Optional[str]) -> Optional[Dict]:
        """
        Normalize contract data from API response
        
        Args:
            contract: Raw contract data from API
            symbol: Underlying symbol
            date: Snapshot date
            
        Returns:
            Normalized contract dictionary
        """
        try:
            # Massive API structure:
            # - details.contract_type, details.expiration_date, details.strike_price
            # - day.close (option price)
            # - greeks.delta, greeks.gamma, greeks.theta, greeks.vega
            # - underlying_asset.price
            # - implied_volatility (top level)
            # - open_interest (top level)
            
            # Extract from nested structure
            details = contract.get('details', {})
            day = contract.get('day', {})
            greeks = contract.get('greeks', {})
            underlying = contract.get('underlying_asset', {})
            
            # Get expiration date
            expiration_date = (
                details.get('expiration_date') or 
                contract.get('expiration_date') or 
                contract.get('expiry')
            )
            
            # Get strike price
            strike = float(
                details.get('strike_price') or 
                contract.get('strike_price') or 
                contract.get('strike') or 
                0
            )
            
            # Get option type
            option_type = (
                details.get('contract_type') or 
                contract.get('contract_type') or 
                contract.get('type') or 
                'call'
            ).lower()
            
            # Get option price (use day.close as last price)
            option_price = float(
                day.get('close') or 
                day.get('last') or 
                contract.get('last') or 
                contract.get('last_price') or 
                0
            )
            
            # Get bid/ask (may not be available in this API format)
            bid = float(
                day.get('bid') or 
                contract.get('bid') or 
                contract.get('bid_price') or 
                0
            )
            ask = float(
                day.get('ask') or 
                contract.get('ask') or 
                contract.get('ask_price') or 
                0
            )
            
            # If no bid/ask, use close price as mid
            if bid == 0 and ask == 0 and option_price > 0:
                bid = option_price * 0.99  # Estimate
                ask = option_price * 1.01  # Estimate
            
            normalized = {
                'symbol': symbol,
                'date': date or datetime.now().strftime('%Y-%m-%d'),
                'expiration_date': expiration_date,
                'strike': strike,
                'option_type': option_type,
                'bid': bid,
                'ask': ask,
                'last': option_price,
                'volume': int(day.get('volume', contract.get('volume', 0)) or 0),
                'open_interest': int(contract.get('open_interest', contract.get('oi', 0)) or 0),
                'implied_volatility': float(contract.get('implied_volatility', contract.get('iv', 0)) or 0),
                'delta': float(greeks.get('delta', contract.get('delta', 0)) or 0),
                'gamma': float(greeks.get('gamma', contract.get('gamma', 0)) or 0),
                'theta': float(greeks.get('theta', contract.get('theta', 0)) or 0),
                'vega': float(greeks.get('vega', contract.get('vega', 0)) or 0),
                'underlying_price': float(
                    underlying.get('price') or 
                    contract.get('underlying_price') or 
                    contract.get('spot') or 
                    0
                ),
            }
            
            # Validate required fields
            if not normalized['expiration_date'] or normalized['strike'] == 0:
                logger.debug(f"Invalid contract: missing expiration or strike. Exp: {expiration_date}, Strike: {strike}")
                return None
            
            return normalized
            
        except Exception as e:
            logger.debug(f"Error normalizing contract: {e}", exc_info=True)
            return None
    
    def get_historical_iv(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        expiration_date: Optional[str] = None,
        strike: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Get historical IV data
        
        Args:
            symbol: Underlying symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            expiration_date: Filter by expiration date or None for all
            strike: Filter by strike price or None for all
            
        Returns:
            DataFrame with columns: date, expiration_date, strike, option_type, implied_volatility, underlying_price
        """
        if not self.is_available():
            return pd.DataFrame()
        
        # Check database first
        cached = self._get_iv_from_db(symbol, start_date, end_date, expiration_date, strike)
        if not cached.empty:
            logger.debug(f"Using cached IV data for {symbol}")
            return cached
        
        try:
            # Collect IV data day by day
            iv_data = []
            current_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            while current_date <= end_dt:
                date_str = current_date.strftime('%Y-%m-%d')
                
                # Get options chain for this date
                chain = self.get_options_chain(symbol, expiration_date=expiration_date, date=date_str)
                
                for contract in chain:
                    if strike and abs(contract['strike'] - strike) > 0.01:
                        continue
                    
                    iv_data.append({
                        'date': date_str,
                        'expiration_date': contract['expiration_date'],
                        'strike': contract['strike'],
                        'option_type': contract['option_type'],
                        'implied_volatility': contract['implied_volatility'],
                        'underlying_price': contract['underlying_price']
                    })
                
                current_date += timedelta(days=1)
                
                # Rate limiting for historical data collection
                time.sleep(0.2)
            
            if not iv_data:
                return pd.DataFrame()
            
            df = pd.DataFrame(iv_data)
            df['date'] = pd.to_datetime(df['date'])
            
            # Store in database
            self._store_iv_in_db(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical IV for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_options_chain_at_date(
        self,
        symbol: str,
        date: str,
        expiration_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Get point-in-time options chain snapshot
        
        Args:
            symbol: Underlying symbol
            date: Snapshot date (YYYY-MM-DD)
            expiration_date: Filter by expiration date or None for all
            
        Returns:
            List of option contracts at that date
        """
        return self.get_options_chain(symbol, expiration_date=expiration_date, date=date)
    
    def get_expiration_dates(self, symbol: str, date: Optional[str] = None) -> List[str]:
        """
        Get available expiration dates for a symbol
        
        Args:
            symbol: Underlying symbol
            date: Historical date or None for current
            
        Returns:
            Sorted list of expiration dates (YYYY-MM-DD)
        """
        chain = self.get_options_chain(symbol, date=date)
        if not chain:
            return []
        
        expirations = sorted(set(c['expiration_date'] for c in chain if c.get('expiration_date')))
        return expirations
    
    # Database methods
    def _store_chain_in_db(self, symbol: str, date: str, contracts: List[Dict]):
        """Store options chain in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for contract in contracts:
                cursor.execute('''
                    INSERT OR REPLACE INTO options_chains
                    (symbol, date, expiration_date, strike, option_type, bid, ask, last,
                     volume, open_interest, implied_volatility, delta, gamma, theta, vega, underlying_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contract['symbol'],
                    contract['date'],
                    contract['expiration_date'],
                    contract['strike'],
                    contract['option_type'],
                    contract['bid'],
                    contract['ask'],
                    contract['last'],
                    contract['volume'],
                    contract['open_interest'],
                    contract['implied_volatility'],
                    contract['delta'],
                    contract['gamma'],
                    contract['theta'],
                    contract['vega'],
                    contract['underlying_price']
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing chain in database: {e}")
    
    def _store_iv_in_db(self, df: pd.DataFrame):
        """Store IV history in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT OR REPLACE INTO iv_history
                    (symbol, date, expiration_date, strike, implied_volatility, underlying_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('symbol', ''),
                    row['date'].strftime('%Y-%m-%d'),
                    row.get('expiration_date', ''),
                    row.get('strike', 0),
                    row.get('implied_volatility', 0),
                    row.get('underlying_price', 0)
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing IV in database: {e}")
    
    def _get_iv_from_db(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        expiration_date: Optional[str] = None,
        strike: Optional[float] = None
    ) -> pd.DataFrame:
        """Get IV history from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = '''
                SELECT date, expiration_date, strike, implied_volatility, underlying_price
                FROM iv_history
                WHERE symbol = ? AND date >= ? AND date <= ?
            '''
            params = [symbol, start_date, end_date]
            
            if expiration_date:
                query += ' AND expiration_date = ?'
                params.append(expiration_date)
            
            if strike:
                query += ' AND ABS(strike - ?) < 0.01'
                params.append(strike)
            
            query += ' ORDER BY date, expiration_date, strike'
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error reading IV from database: {e}")
            return pd.DataFrame()
    
    # Cache methods
    def _cache_chain(self, symbol: str, date: str, contracts: List[Dict]):
        """Cache chain to file"""
        try:
            cache_file = self.cache_dir / f"{symbol}_{date}.json"
            with open(cache_file, 'w') as f:
                json.dump(contracts, f, indent=2)
        except Exception as e:
            logger.debug(f"Error caching chain: {e}")
    
    def _get_cached_chain(self, symbol: str, date: str, expiration_date: Optional[str]) -> Optional[List[Dict]]:
        """Get cached chain from file"""
        try:
            cache_file = self.cache_dir / f"{symbol}_{date}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    contracts = json.load(f)
                
                if expiration_date:
                    contracts = [c for c in contracts if c.get('expiration_date') == expiration_date]
                
                return contracts
        except Exception as e:
            logger.debug(f"Error reading cached chain: {e}")
        
        return None

