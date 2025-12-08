"""
GEX (Gamma Exposure) Proxy Calculator
Calculates proxy for Gamma Exposure based on options chain
"""
import logging
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

class GEXCalculator:
    """Calculate GEX Proxy"""
    
    def __init__(self):
        """Initialize GEX calculator"""
        pass
    
    def calculate_gex_proxy(
        self,
        options_chain: List[Dict],
        spot_price: float
    ) -> Dict:
        """
        Calculate GEX Proxy
        
        GEX Proxy = Sum of (Open Interest * Gamma * Spot Price * 100)
        for all options in chain
        
        Positive GEX = Market makers are long gamma (supports price)
        Negative GEX = Market makers are short gamma (volatility expansion)
        
        Args:
            options_chain: List of option contracts with OI and Greeks
            spot_price: Current spot price
            
        Returns:
            Dictionary with total GEX, call GEX, put GEX, and levels
        """
        if not options_chain:
            return {
                'total_gex': 0.0,
                'call_gex': 0.0,
                'put_gex': 0.0,
                'gex_levels': {},
                'max_pain': 0.0
            }
        
        total_gex = 0.0
        call_gex = 0.0
        put_gex = 0.0
        gex_levels = {}  # strike -> gex
        max_pain_data = {}  # strike -> total OI
        
        for contract in options_chain:
            try:
                strike = float(contract.get('strike_price', 0))
                open_interest = float(contract.get('open_interest', 0))
                option_type = contract.get('type', '').lower()
                gamma = float(contract.get('gamma', 0))
                
                if strike == 0 or open_interest == 0:
                    continue
                
                # Calculate GEX contribution
                # GEX = OI * Gamma * Spot * 100 * multiplier
                # For calls: positive contribution
                # For puts: negative contribution
                gex_contribution = open_interest * gamma * spot_price * 100
                
                if option_type == 'call':
                    call_gex += gex_contribution
                    total_gex += gex_contribution
                elif option_type == 'put':
                    put_gex -= gex_contribution  # Puts have negative GEX
                    total_gex -= gex_contribution
                
                # Track GEX by strike
                if strike not in gex_levels:
                    gex_levels[strike] = 0.0
                
                if option_type == 'call':
                    gex_levels[strike] += gex_contribution
                else:
                    gex_levels[strike] -= gex_contribution
                
                # Track for max pain calculation
                if strike not in max_pain_data:
                    max_pain_data[strike] = 0
                max_pain_data[strike] += open_interest
                
            except Exception as e:
                logger.debug(f"Error processing contract for GEX: {e}")
                continue
        
        # Calculate max pain (strike with highest total OI)
        max_pain = max(max_pain_data.items(), key=lambda x: x[1])[0] if max_pain_data else spot_price
        
        return {
            'total_gex': total_gex,
            'call_gex': call_gex,
            'put_gex': put_gex,
            'gex_levels': gex_levels,
            'max_pain': max_pain,
            'net_gex': call_gex + put_gex  # Net GEX
        }
    
    def interpret_gex(self, gex_data: Dict) -> str:
        """
        Interpret GEX data
        
        Args:
            gex_data: GEX calculation results
            
        Returns:
            Interpretation string
        """
        total_gex = gex_data.get('total_gex', 0)
        
        if total_gex > 1_000_000_000:  # > 1B
            return "EXTREMELY_POSITIVE"  # Very supportive
        elif total_gex > 100_000_000:  # > 100M
            return "POSITIVE"  # Supportive
        elif total_gex > -100_000_000:  # Between -100M and 100M
            return "NEUTRAL"
        elif total_gex > -1_000_000_000:  # Between -1B and -100M
            return "NEGATIVE"  # Volatility expansion likely
        else:  # < -1B
            return "EXTREMELY_NEGATIVE"  # Very negative, high volatility risk

