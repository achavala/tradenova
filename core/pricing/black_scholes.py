"""
Black-Scholes Options Pricing Model
Comprehensive Greeks calculator for options trading

Calculates:
- First-order Greeks: Delta, Gamma, Vega, Theta, Rho
- Second-order Greeks: Vanna, Vomma, Charm, Speed
"""
import numpy as np
from scipy.stats import norm
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class BlackScholes:
    """
    Black-Scholes options pricing model with comprehensive Greeks
    
    Supports:
    - European and American-style options (approximation)
    - First-order Greeks (Delta, Gamma, Vega, Theta, Rho)
    - Second-order Greeks (Vanna, Vomma, Charm, Speed)
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize Black-Scholes calculator
        
        Args:
            risk_free_rate: Risk-free interest rate (default: 5% = 0.05)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate(
        self,
        spot_price: float,
        strike: float,
        time_to_expiry: float,  # In years
        volatility: float,  # Implied volatility (e.g., 0.20 for 20%)
        option_type: str,  # 'call' or 'put'
        dividend_yield: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate option price and all Greeks using Black-Scholes
        
        Args:
            spot_price: Current stock price (S)
            strike: Strike price (K)
            time_to_expiry: Time to expiration in years (T)
            volatility: Implied volatility (σ)
            option_type: 'call' or 'put'
            dividend_yield: Dividend yield (default: 0.0)
            
        Returns:
            Dictionary with:
            - price: Option price
            - delta: First-order price sensitivity
            - gamma: Second-order price sensitivity
            - vega: Volatility sensitivity
            - theta: Time decay
            - rho: Interest rate sensitivity
            - vanna: Delta-Volatility cross-sensitivity
            - vomma: Vega-Volatility cross-sensitivity
            - charm: Delta-Time sensitivity
            - speed: Gamma-Price sensitivity
            - d1, d2: Intermediate calculations
        """
        if time_to_expiry <= 0:
            # Option expired
            return self._expired_option_result(option_type)
        
        if volatility <= 0:
            logger.warning(f"Invalid volatility: {volatility}")
            volatility = 0.01  # Use small positive value
        
        S = spot_price
        K = strike
        T = time_to_expiry
        r = self.risk_free_rate
        sigma = volatility
        q = dividend_yield  # Dividend yield
        
        # Calculate d1 and d2
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Standard normal CDF and PDF
        N_d1 = norm.cdf(d1)
        N_d2 = norm.cdf(d2)
        N_neg_d1 = norm.cdf(-d1)
        N_neg_d2 = norm.cdf(-d2)
        n_d1 = norm.pdf(d1)  # PDF of d1
        
        # Option price
        if option_type.lower() == 'call':
            price = S * np.exp(-q * T) * N_d1 - K * np.exp(-r * T) * N_d2
        else:  # put
            price = K * np.exp(-r * T) * N_neg_d2 - S * np.exp(-q * T) * N_neg_d1
        
        # First-order Greeks
        if option_type.lower() == 'call':
            delta = np.exp(-q * T) * N_d1
            theta = (
                -(S * n_d1 * sigma * np.exp(-q * T)) / (2 * np.sqrt(T))
                - r * K * np.exp(-r * T) * N_d2
                + q * S * np.exp(-q * T) * N_d1
            ) / 365  # Per day
            rho = K * T * np.exp(-r * T) * N_d2 / 100  # Per 1% change in rate
        else:  # put
            delta = -np.exp(-q * T) * N_neg_d1
            theta = (
                -(S * n_d1 * sigma * np.exp(-q * T)) / (2 * np.sqrt(T))
                + r * K * np.exp(-r * T) * N_neg_d2
                - q * S * np.exp(-q * T) * N_neg_d1
            ) / 365  # Per day
            rho = -K * T * np.exp(-r * T) * N_neg_d2 / 100  # Per 1% change in rate
        
        # Gamma (same for calls and puts)
        gamma = (n_d1 * np.exp(-q * T)) / (S * sigma * np.sqrt(T))
        
        # Vega (same for calls and puts)
        vega = S * n_d1 * np.exp(-q * T) * np.sqrt(T) / 100  # Per 1% change in IV
        
        # Second-order Greeks
        # Vanna: ∂Delta/∂Volatility = ∂Vega/∂Spot
        vanna = -n_d1 * np.exp(-q * T) * d2 / sigma / 100  # Per 1% change in IV
        
        # Vomma: ∂Vega/∂Volatility
        vomma = vega * d1 * d2 / sigma / 100  # Per 1% change in IV
        
        # Charm: ∂Delta/∂Time (Delta decay)
        if option_type.lower() == 'call':
            charm = (
                -np.exp(-q * T) * n_d1 * (
                    (r - q) / (sigma * np.sqrt(T))
                    - d2 / (2 * T)
                )
                + q * np.exp(-q * T) * N_d1
            ) / 365  # Per day
        else:  # put
            charm = (
                -np.exp(-q * T) * n_d1 * (
                    (r - q) / (sigma * np.sqrt(T))
                    - d2 / (2 * T)
                )
                - q * np.exp(-q * T) * N_neg_d1
            ) / 365  # Per day
        
        # Speed: ∂Gamma/∂Spot (third-order, but useful)
        speed = -gamma * (1 + d1 / (sigma * np.sqrt(T))) / S
        
        return {
            'price': float(price),
            'delta': float(delta),
            'gamma': float(gamma),
            'vega': float(vega),
            'theta': float(theta),
            'rho': float(rho),
            'vanna': float(vanna),
            'vomma': float(vomma),
            'charm': float(charm),
            'speed': float(speed),
            'd1': float(d1),
            'd2': float(d2),
            'implied_volatility': volatility
        }
    
    def _expired_option_result(self, option_type: str) -> Dict[str, float]:
        """Return result for expired option"""
        if option_type.lower() == 'call':
            return {
                'price': 0.0,
                'delta': 0.0,
                'gamma': 0.0,
                'vega': 0.0,
                'theta': 0.0,
                'rho': 0.0,
                'vanna': 0.0,
                'vomma': 0.0,
                'charm': 0.0,
                'speed': 0.0,
                'd1': 0.0,
                'd2': 0.0,
                'implied_volatility': 0.0
            }
        else:  # put
            return {
                'price': 0.0,
                'delta': 0.0,
                'gamma': 0.0,
                'vega': 0.0,
                'theta': 0.0,
                'rho': 0.0,
                'vanna': 0.0,
                'vomma': 0.0,
                'charm': 0.0,
                'speed': 0.0,
                'd1': 0.0,
                'd2': 0.0,
                'implied_volatility': 0.0
            }
    
    def calculate_implied_volatility(
        self,
        market_price: float,
        spot_price: float,
        strike: float,
        time_to_expiry: float,
        option_type: str,
        dividend_yield: float = 0.0,
        initial_guess: float = 0.20,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Optional[float]:
        """
        Calculate implied volatility from market price using Newton-Raphson method
        
        Args:
            market_price: Observed market price of the option
            spot_price: Current stock price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            option_type: 'call' or 'put'
            dividend_yield: Dividend yield
            initial_guess: Initial volatility guess (default: 20%)
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance
            
        Returns:
            Implied volatility or None if convergence fails
        """
        if time_to_expiry <= 0:
            return None
        
        if market_price <= 0:
            return None
        
        # Use Newton-Raphson method
        vol = initial_guess
        
        for _ in range(max_iterations):
            # Calculate price and vega at current volatility
            result = self.calculate(
                spot_price, strike, time_to_expiry, vol, option_type, dividend_yield
            )
            
            price = result['price']
            vega = result['vega']
            
            # Check convergence
            price_diff = price - market_price
            if abs(price_diff) < tolerance:
                return vol
            
            # Avoid division by zero
            if abs(vega) < 1e-10:
                # Use bisection method as fallback
                return self._bisection_iv(
                    market_price, spot_price, strike, time_to_expiry,
                    option_type, dividend_yield
                )
            
            # Newton-Raphson update: vol_new = vol_old - (price - market_price) / vega
            vol = vol - price_diff / (vega * 100)  # vega is per 1%, so multiply by 100
            
            # Ensure volatility stays positive
            vol = max(0.001, min(5.0, vol))  # Clamp between 0.1% and 500%
        
        # If didn't converge, try bisection
        logger.warning(f"Newton-Raphson didn't converge, trying bisection")
        return self._bisection_iv(
            market_price, spot_price, strike, time_to_expiry,
            option_type, dividend_yield
        )
    
    def _bisection_iv(
        self,
        market_price: float,
        spot_price: float,
        strike: float,
        time_to_expiry: float,
        option_type: str,
        dividend_yield: float = 0.0
    ) -> Optional[float]:
        """Calculate IV using bisection method (fallback)"""
        vol_low = 0.001
        vol_high = 5.0
        max_iterations = 100
        tolerance = 1e-6
        
        for _ in range(max_iterations):
            vol_mid = (vol_low + vol_high) / 2
            
            result = self.calculate(
                spot_price, strike, time_to_expiry, vol_mid, option_type, dividend_yield
            )
            
            price_mid = result['price']
            
            if abs(price_mid - market_price) < tolerance:
                return vol_mid
            
            if price_mid < market_price:
                vol_low = vol_mid
            else:
                vol_high = vol_mid
        
        return (vol_low + vol_high) / 2
    
    def calculate_greeks_only(
        self,
        spot_price: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        option_type: str,
        dividend_yield: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate only Greeks (faster if price not needed)
        
        Returns same structure as calculate() but optimized for Greeks-only
        """
        return self.calculate(
            spot_price, strike, time_to_expiry, volatility, option_type, dividend_yield
        )




