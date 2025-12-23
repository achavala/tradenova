"""
Earnings Calendar Service
Fetches earnings dates from multiple sources (Alpha Vantage, Polygon/Massive, etc.)
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
import requests
from config import Config

logger = logging.getLogger(__name__)

class EarningsCalendar:
    """
    Earnings calendar service
    
    Supports multiple data sources:
    - Alpha Vantage (free tier available)
    - Polygon/Massive API (if available)
    - Manual fallback
    """
    
    def __init__(self):
        """Initialize earnings calendar"""
        self.alpha_vantage_api_key = Config.ALPHA_VANTAGE_API_KEY if hasattr(Config, 'ALPHA_VANTAGE_API_KEY') else None
        self.massive_api_key = Config.MASSIVE_API_KEY
        
        # Cache for earnings dates
        self._earnings_cache: Dict[str, List[date]] = {}
        self._cache_date = None
    
    def get_earnings_dates(
        self,
        symbol: str,
        lookahead_days: int = 90
    ) -> List[date]:
        """
        Get upcoming earnings dates for a symbol
        
        Args:
            symbol: Stock symbol
            lookahead_days: Number of days to look ahead (default: 90)
            
        Returns:
            List of earnings dates
        """
        # Check cache
        today = date.today()
        if self._cache_date != today:
            self._earnings_cache = {}
            self._cache_date = today
        
        if symbol in self._earnings_cache:
            return self._earnings_cache[symbol]
        
        earnings_dates = []
        
        # Try Alpha Vantage first (if API key available)
        if self.alpha_vantage_api_key:
            try:
                earnings_dates = self._get_alpha_vantage_earnings(symbol, lookahead_days)
                if earnings_dates:
                    logger.info(f"Retrieved {len(earnings_dates)} earnings dates for {symbol} from Alpha Vantage")
                    self._earnings_cache[symbol] = earnings_dates
                    return earnings_dates
            except Exception as e:
                logger.debug(f"Alpha Vantage earnings fetch failed for {symbol}: {e}")
        
        # Try Polygon/Massive API
        if self.massive_api_key:
            try:
                earnings_dates = self._get_polygon_earnings(symbol, lookahead_days)
                if earnings_dates:
                    logger.info(f"Retrieved {len(earnings_dates)} earnings dates for {symbol} from Polygon/Massive")
                    self._earnings_cache[symbol] = earnings_dates
                    return earnings_dates
            except Exception as e:
                logger.warning(f"Polygon earnings fetch failed for {symbol}: {e}")
        
        # Fallback: Return empty list (can be populated manually)
        logger.warning(f"No earnings dates found for {symbol} - consider manual entry")
        self._earnings_cache[symbol] = []
        return []
    
    def _get_alpha_vantage_earnings(
        self,
        symbol: str,
        lookahead_days: int
    ) -> List[date]:
        """
        Get earnings from Alpha Vantage API
        
        Note: Alpha Vantage Earnings Calendar endpoint may require premium subscription.
        This implementation attempts to fetch but gracefully falls back if unavailable.
        
        Args:
            symbol: Stock symbol
            lookahead_days: Days to look ahead
            
        Returns:
            List of earnings dates
        """
        if not self.alpha_vantage_api_key:
            return []
        
        try:
            # Alpha Vantage Earnings Calendar endpoint
            # Note: This may require premium subscription
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'EARNINGS_CALENDAR',
                'symbol': symbol,
                'horizon': '3month',
                'apikey': self.alpha_vantage_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            # Check if response is CSV (text) or JSON
            content_type = response.headers.get('content-type', '')
            
            if 'text/csv' in content_type or response.text.startswith('symbol,'):
                # Parse CSV format
                lines = response.text.strip().split('\n')
                if len(lines) > 1:
                    earnings_dates = []
                    for line in lines[1:]:  # Skip header
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 2:
                            try:
                                # Date is typically in second column
                                earnings_date = datetime.strptime(parts[1], '%Y-%m-%d').date()
                                today = date.today()
                                if earnings_date >= today and (earnings_date - today).days <= lookahead_days:
                                    earnings_dates.append(earnings_date)
                            except (ValueError, IndexError):
                                continue
                    return sorted(earnings_dates)
            else:
                # Try JSON format
                try:
                    data = response.json()
                    
                    # Check for error messages
                    if 'Error Message' in data or 'Note' in data:
                        logger.debug(f"Alpha Vantage API limitation for {symbol}: {data.get('Error Message') or data.get('Note')}")
                        return []
                    
                    # JSON format
                    if 'earningsCalendar' in data:
                        earnings_dates = []
                        for item in data['earningsCalendar']:
                            try:
                                earnings_date = datetime.strptime(item['reportDate'], '%Y-%m-%d').date()
                                today = date.today()
                                if earnings_date >= today and (earnings_date - today).days <= lookahead_days:
                                    earnings_dates.append(earnings_date)
                            except (ValueError, KeyError):
                                continue
                        return sorted(earnings_dates)
                except ValueError:
                    # Not JSON, might be CSV
                    pass
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Alpha Vantage API request failed for {symbol}: {e}")
        except Exception as e:
            logger.debug(f"Error parsing Alpha Vantage earnings for {symbol}: {e}")
        
        return []
    
    def _get_polygon_earnings(
        self,
        symbol: str,
        lookahead_days: int
    ) -> List[date]:
        """
        Get earnings from Polygon/Massive API
        
        Args:
            symbol: Stock symbol
            lookahead_days: Days to look ahead
            
        Returns:
            List of earnings dates
        """
        if not self.massive_api_key:
            return []
        
        try:
            url = f"https://api.polygon.io/v2/reference/financials"
            params = {
                'ticker': symbol,
                'timeframe': 'quarterly',
                'limit': 4,  # Next 4 quarters
                'apiKey': self.massive_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK' and 'results' in data:
                earnings_dates = []
                cutoff_date = date.today() + timedelta(days=lookahead_days)
                
                for result in data['results']:
                    # Look for earnings date in financials
                    if 'end_date' in result:
                        try:
                            earnings_date = datetime.strptime(result['end_date'], '%Y-%m-%d').date()
                            if date.today() <= earnings_date <= cutoff_date:
                                earnings_dates.append(earnings_date)
                        except:
                            continue
                
                return sorted(earnings_dates)
            
        except Exception as e:
            logger.debug(f"Polygon earnings API not available or error: {e}")
        
        return []
    
    def get_all_tickers_earnings(
        self,
        symbols: List[str],
        lookahead_days: int = 90
    ) -> Dict[str, List[date]]:
        """
        Get earnings dates for all tickers
        
        Args:
            symbols: List of stock symbols
            lookahead_days: Days to look ahead
            
        Returns:
            Dictionary mapping symbol -> list of earnings dates
        """
        all_earnings = {}
        
        for symbol in symbols:
            earnings_dates = self.get_earnings_dates(symbol, lookahead_days)
            if earnings_dates:
                all_earnings[symbol] = earnings_dates
        
        return all_earnings
    
    def update_gap_risk_monitor(
        self,
        gap_risk_monitor,
        symbols: List[str],
        lookahead_days: int = 90
    ):
        """
        Update Gap Risk Monitor with earnings dates
        
        Args:
            gap_risk_monitor: GapRiskMonitor instance
            symbols: List of stock symbols
            lookahead_days: Days to look ahead
        """
        all_earnings = self.get_all_tickers_earnings(symbols, lookahead_days)
        
        for symbol, earnings_dates in all_earnings.items():
            for earnings_date in earnings_dates:
                gap_risk_monitor.add_earnings_date(symbol, earnings_date)
        
        logger.info(f"Updated Gap Risk Monitor with earnings dates for {len(all_earnings)} symbols")

