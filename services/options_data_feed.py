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
            
            # Handle different response formats
            if isinstance(data, dict):
                # If response is a dict, check for common keys
                if 'contracts' in data:
                    contracts = data['contracts']
                elif 'results' in data:
                    contracts = data['results']
                else:
                    # If it's a dict but no expected keys, try to extract values
                    contracts = list(data.values()) if data else []
            elif isinstance(data, list):
                contracts = data
            else:
                logger.warning(f"Unexpected response format for {symbol}: {type(data)}")
                return []
            
            # Flatten nested lists (Alpaca sometimes returns list of lists)
            flattened = []
            for item in contracts:
                if isinstance(item, list):
                    flattened.extend(item)
                elif isinstance(item, dict):
                    flattened.append(item)
            
            logger.info(f"Retrieved {len(flattened)} option contracts for {symbol}")
            return flattened
            
        except Exception as e:
            logger.error(f"Error fetching options chain for {symbol}: {e}")
            return []
    
    def get_option_quote(self, option_symbol: str) -> Optional[Dict]:
        """
        Get real-time quote for an option
        
        Args:
            option_symbol: Option contract symbol (e.g., "AAPL240119C00150000")
            
        Returns:
            Quote dictionary with bid, ask, last, etc.
        """
        try:
            # Use Alpaca's latest trade/quote endpoint
            latest_trade = self.api.get_latest_trade(option_symbol)
            latest_quote = self.api.get_latest_quote(option_symbol)
            
            if not latest_trade and not latest_quote:
                return None
            
            quote = {
                'symbol': option_symbol,
                'bid': float(latest_quote.bp) if latest_quote else None,
                'ask': float(latest_quote.ap) if latest_quote else None,
                'last': float(latest_trade.price) if latest_trade else None,
                'bid_size': int(latest_quote.bs) if latest_quote else None,
                'ask_size': int(latest_quote.as_) if latest_quote else None,
                'volume': int(latest_trade.size) if latest_trade else None,
                'timestamp': latest_trade.timestamp if latest_trade else None
            }
            
            return quote
            
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
        option_type: str = 'call',
        available_contracts: Optional[List[Dict]] = None
    ) -> Optional[Dict]:
        """
        Get at-the-money option for a symbol
        
        Args:
            symbol: Underlying symbol
            expiration_date: Optional expiration date
            option_type: 'call' or 'put'
            available_contracts: Optional pre-filtered list of contracts (Phase-0: for liquidity-filtered options)
            
        Returns:
            Option contract closest to ATM
        """
        try:
            # Get current stock price
            current_price = self.client.get_latest_price(symbol)
            if not current_price:
                return None
            
            # Use provided contracts if available (Phase-0: liquidity-filtered), otherwise fetch
            if available_contracts is not None:
                chain = available_contracts
            else:
                # Get options chain
                chain = self.get_options_chain(symbol, expiration_date)
                if not chain:
                    return None
            
            # Filter by type
            filtered = [
                c for c in chain 
                if c.get('type', '').lower() == option_type.lower()
            ]
            
            if not filtered:
                return None
            
            # Find closest to ATM
            atm_option = min(
                filtered,
                key=lambda x: abs(float(x.get('strike_price', 0)) - current_price)
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
            # Handle case where chain items might be strings, dicts, or lists
            expirations = []
            for c in chain:
                if isinstance(c, dict):
                    exp_date = c.get('expiration_date')
                    if exp_date:
                        expirations.append(str(exp_date))  # Ensure string format
                elif isinstance(c, list):
                    # If it's a list, extract from each item
                    for item in c:
                        if isinstance(item, dict):
                            exp_date = item.get('expiration_date')
                            if exp_date:
                                expirations.append(str(exp_date))
                elif isinstance(c, str):
                    # If it's a string, skip (shouldn't happen but handle gracefully)
                    continue
            
            expirations = sorted(set(expirations))
            
            return expirations
            
        except Exception as e:
            logger.error(f"Error getting expiration dates for {symbol}: {e}")
            return []

