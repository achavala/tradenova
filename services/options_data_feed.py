"""
Options Data Feed Service
Fetches options chain data, quotes, and Greeks from Alpaca
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import requests
from alpaca_client import AlpacaClient

logger = logging.getLogger(__name__)

class OptionsDataFeed:
    """Options data feed service"""
    
    def __init__(self, alpaca_client: AlpacaClient):
        """
        Initialize options data feed
        
        Args:
            alpaca_client: Alpaca client instance
        """
        self.client = alpaca_client
        self.api = alpaca_client.api
        self.base_url = alpaca_client.ALPACA_BASE_URL
    
    def get_options_chain(
        self, 
        symbol: str, 
        expiration_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Get options chain for a symbol
        
        Args:
            symbol: Underlying symbol
            expiration_date: Optional expiration date (YYYY-MM-DD)
            
        Returns:
            List of option contracts
        """
        try:
            # Alpaca Options API endpoint
            # Note: Alpaca's options API structure - adjust if needed
            url = f"{self.base_url}/v2/options/contracts"
            # Get credentials from API object
            api_key = getattr(self.api, '_key_id', '')
            secret_key = getattr(self.api, '_secret_key', '')
            headers = {
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": secret_key
            }
            
            params = {
                "underlying_symbols": symbol,
                "status": "active"
            }
            
            if expiration_date:
                params["expiration_date"] = expiration_date
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Alpaca returns a dict with 'option_contracts' key
            if isinstance(data, dict):
                contracts = data.get('option_contracts', data.get('contracts', data.get('data', [])))
            else:
                contracts = data if isinstance(data, list) else []
            
            logger.info(f"Retrieved {len(contracts)} option contracts for {symbol}")
            return contracts
            
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {e}")
            return []
    
    def get_option_quote(self, option_symbol: str) -> Optional[Dict]:
        """
        Get latest NBBO quote for an option using /v2/options/quotes/latest endpoint
        
        This endpoint works even when market is closed and returns last-known NBBO quotes.
        This is exactly what the Alpaca web interface uses.
        
        Priority:
        1. NBBO quote from /v2/options/quotes/latest (works even when market closed)
        2. Last trade price - fallback when NBBO unavailable
        
        Args:
            option_symbol: Option contract symbol (e.g., "AAPL240119C00150000")
            
        Returns:
            Quote dictionary with bid, ask, mid, etc. or None if no price available
        """
        try:
            # ✅ CRITICAL: Use get_latest_quote() which works for options (NBBO)
            # This is the standard Alpaca SDK method that handles options quotes
            # It uses the correct endpoint internally and works even when market is closed
            try:
                latest_quote = self.api.get_latest_quote(option_symbol)
                if latest_quote:
                    # Extract bid/ask from quote object
                    bid = float(latest_quote.bp) if hasattr(latest_quote, 'bp') and latest_quote.bp else None
                    ask = float(latest_quote.ap) if hasattr(latest_quote, 'ap') and latest_quote.ap else None
                    bid_size = int(latest_quote.bs) if hasattr(latest_quote, 'bs') and latest_quote.bs else None
                    ask_size = int(latest_quote.as_) if hasattr(latest_quote, 'as_') and latest_quote.as_ else None
                    timestamp = latest_quote.timestamp if hasattr(latest_quote, 'timestamp') else None
                    
                    # If we have both bid and ask, use mid price (ideal case)
                    if bid is not None and ask is not None and bid > 0 and ask > 0:
                        mid = (bid + ask) / 2
                        return {
                            'symbol': option_symbol,
                            'bid': bid,
                            'ask': ask,
                            'mid': mid,
                            'bid_size': bid_size,
                            'ask_size': ask_size,
                            'source': 'NBBO',
                            'timestamp': timestamp
                        }
                    # If only bid exists, use it
                    elif bid is not None and bid > 0:
                        return {
                            'symbol': option_symbol,
                            'bid': bid,
                            'ask': None,
                            'mid': bid,
                            'bid_size': bid_size,
                            'ask_size': None,
                            'source': 'NBBO_bid',
                            'timestamp': timestamp
                        }
                    # If only ask exists, use it
                    elif ask is not None and ask > 0:
                        return {
                            'symbol': option_symbol,
                            'bid': None,
                            'ask': ask,
                            'mid': ask,
                            'bid_size': None,
                            'ask_size': ask_size,
                            'source': 'NBBO_ask',
                            'timestamp': timestamp
                        }
            except Exception as e:
                logger.debug(f"  NBBO quote error for {option_symbol}: {e}")
            
            # 2) Fallback: Try alternative endpoint format
            try:
                latest_quote = self.api.get_latest_quote(option_symbol)
                if latest_quote:
                    bid = float(latest_quote.bp) if latest_quote.bp else None
                    ask = float(latest_quote.ap) if latest_quote.ap else None
                    
                    if bid is not None and ask is not None and bid > 0 and ask > 0:
                        mid = (bid + ask) / 2
                        return {
                            'symbol': option_symbol,
                            'bid': bid,
                            'ask': ask,
                            'mid': mid,
                            'bid_size': int(latest_quote.bs) if latest_quote.bs else None,
                            'ask_size': int(latest_quote.as_) if latest_quote.as_ else None,
                            'source': 'NBBO_fallback',
                            'timestamp': latest_quote.timestamp if hasattr(latest_quote, 'timestamp') else None
                        }
            except Exception as e:
                logger.debug(f"  Standard quote fallback error for {option_symbol}: {e}")
            
            # 3) Fallback: Last trade price
            try:
                latest_trade = self.api.get_latest_trade(option_symbol)
                if latest_trade and latest_trade.price:
                    price = float(latest_trade.price)
                    if price > 0:
                        return {
                            'symbol': option_symbol,
                            'bid': None,
                            'ask': None,
                            'last': price,
                            'mid': price,
                            'volume': int(latest_trade.size) if latest_trade.size else None,
                            'source': 'last_trade',
                            'timestamp': latest_trade.timestamp if hasattr(latest_trade, 'timestamp') else None
                        }
            except Exception as e:
                logger.debug(f"  Last trade error for {option_symbol}: {e}")
            
            # No price available
            return None
            
        except Exception as e:
            logger.debug(f"Error fetching quote for {option_symbol}: {e}")
            return None
    
    def get_option_greeks(self, option_symbol: str) -> Optional[Dict]:
        """
        Get Greeks for an option
        
        Note: Alpaca may not provide Greeks directly.
        This is a placeholder that can be enhanced with:
        - Black-Scholes calculation
        - Third-party data providers
        - Options chain data with implied volatility
        
        Args:
            option_symbol: Option contract symbol
            
        Returns:
            Greeks dictionary (delta, gamma, theta, vega, iv)
        """
        try:
            # Try to get from options chain data
            # For now, return None - will be calculated separately
            # In production, you might use:
            # - Polygon options snapshot
            # - CBOE data
            # - Black-Scholes calculation from chain data
            
            return None
            
        except Exception as e:
            logger.debug(f"Error fetching Greeks for {option_symbol}: {e}")
            return None
    
    def calculate_greeks_black_scholes(
        self,
        spot_price: float,
        strike: float,
        time_to_expiry: float,  # In years
        risk_free_rate: float,
        volatility: float,  # Implied volatility
        option_type: str  # 'call' or 'put'
    ) -> Dict:
        """
        Calculate Greeks using Black-Scholes model
        
        Args:
            spot_price: Current stock price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            risk_free_rate: Risk-free rate (e.g., 0.05 for 5%)
            volatility: Implied volatility (e.g., 0.20 for 20%)
            option_type: 'call' or 'put'
            
        Returns:
            Dictionary with delta, gamma, theta, vega, iv
        """
        from scipy.stats import norm
        import numpy as np
        
        S = spot_price
        K = strike
        T = time_to_expiry
        r = risk_free_rate
        sigma = volatility
        
        if T <= 0:
            # Option expired
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'iv': volatility
            }
        
        # Calculate d1 and d2
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Delta
        if option_type.lower() == 'call':
            delta = norm.cdf(d1)
        else:  # put
            delta = -norm.cdf(-d1)
        
        # Gamma (same for calls and puts)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        # Theta
        theta_part1 = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
        if option_type.lower() == 'call':
            theta_part2 = -r * K * np.exp(-r * T) * norm.cdf(d2)
        else:  # put
            theta_part2 = r * K * np.exp(-r * T) * norm.cdf(-d2)
        theta = (theta_part1 + theta_part2) / 365  # Per day
        
        # Vega (same for calls and puts)
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # Per 1% change in IV
        
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'iv': volatility
        }
    
    def get_atm_options(
        self,
        symbol: str,
        expiration_date: Optional[str] = None,
        option_type: str = 'call'
    ) -> Optional[Dict]:
        """
        Get at-the-money option for a symbol
        
        Args:
            symbol: Underlying symbol
            expiration_date: Optional expiration date
            option_type: 'call' or 'put'
            
        Returns:
            Option contract closest to ATM
        """
        try:
            # Get current stock price
            current_price = self.client.get_latest_price(symbol)
            if not current_price:
                return None
            
            # Get options chain
            chain = self.get_options_chain(symbol, expiration_date)
            if not chain:
                return None
            
            # Filter by type and handle both dict and object types
            filtered = []
            for c in chain:
                if isinstance(c, dict):
                    contract_type = c.get('type', '') or c.get('option_type', '')
                    strike = float(c.get('strike_price', 0) or c.get('strike', 0))
                else:
                    contract_type = getattr(c, 'type', '') or getattr(c, 'option_type', '')
                    strike = float(getattr(c, 'strike_price', 0) or getattr(c, 'strike', 0))
                
                if contract_type.lower() == option_type.lower():
                    filtered.append((c, strike))
            
            if not filtered:
                return None
            
            # Find closest to ATM
            atm_option, _ = min(
                filtered,
                key=lambda x: abs(x[1] - current_price)
            )
            
            return atm_option
            
        except Exception as e:
            logger.error(f"Error getting ATM option for {symbol}: {e}")
            return None
    
    def get_expiration_dates(self, symbol: str) -> List[str]:
        """
        Get available expiration dates for a symbol
        
        Args:
            symbol: Underlying symbol
            
        Returns:
            List of expiration dates (YYYY-MM-DD)
        """
        try:
            chain = self.get_options_chain(symbol)
            if not chain:
                return []
            
            # Extract unique expiration dates
            # Handle both dict and string/list types
            expirations = set()
            for c in chain:
                if isinstance(c, dict):
                    exp_date = c.get('expiration_date') or c.get('exp_date')
                elif isinstance(c, str):
                    # Skip if it's just a string
                    continue
                else:
                    exp_date = getattr(c, 'expiration_date', None) or getattr(c, 'exp_date', None)
                
                if exp_date:
                    # Convert to string if needed
                    if hasattr(exp_date, 'strftime'):
                        exp_date = exp_date.strftime('%Y-%m-%d')
                    expirations.add(str(exp_date))
            
            return sorted(list(expirations))
            
        except Exception as e:
            logger.error(f"Error getting expiration dates for {symbol}: {e}")
            return []

