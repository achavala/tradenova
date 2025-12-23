#!/usr/bin/env python3
"""
Tests for Black-Scholes Greeks calculator
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from core.pricing.black_scholes import BlackScholes
import numpy as np

class TestBlackScholes(unittest.TestCase):
    """Test Black-Scholes calculator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.bs = BlackScholes(risk_free_rate=0.05)
    
    def test_call_option_price(self):
        """Test call option price calculation"""
        result = self.bs.calculate(
            spot_price=100,
            strike=100,
            time_to_expiry=0.25,  # 3 months
            volatility=0.20,  # 20% IV
            option_type='call'
        )
        
        # ATM call with 20% IV, 3 months to expiry
        # Expected price around $3-4
        self.assertGreater(result['price'], 2.0)
        self.assertLess(result['price'], 5.0)
        self.assertAlmostEqual(result['delta'], 0.5, delta=0.1)  # ATM call delta ~0.5
    
    def test_put_option_price(self):
        """Test put option price calculation"""
        result = self.bs.calculate(
            spot_price=100,
            strike=100,
            time_to_expiry=0.25,
            volatility=0.20,
            option_type='put'
        )
        
        # ATM put should be similar to ATM call (put-call parity)
        self.assertGreater(result['price'], 2.0)
        self.assertLess(result['price'], 5.0)
        self.assertAlmostEqual(result['delta'], -0.5, delta=0.1)  # ATM put delta ~-0.5
    
    def test_delta_values(self):
        """Test delta values for different moneyness"""
        # ITM call
        itm = self.bs.calculate(100, 90, 0.25, 0.20, 'call')
        self.assertGreater(itm['delta'], 0.7)  # ITM call delta > 0.7
        
        # OTM call
        otm = self.bs.calculate(100, 110, 0.25, 0.20, 'call')
        self.assertLess(otm['delta'], 0.3)  # OTM call delta < 0.3
        
        # ATM call
        atm = self.bs.calculate(100, 100, 0.25, 0.20, 'call')
        self.assertAlmostEqual(atm['delta'], 0.5, delta=0.1)
    
    def test_gamma_positive(self):
        """Test that gamma is always positive"""
        result = self.bs.calculate(100, 100, 0.25, 0.20, 'call')
        self.assertGreater(result['gamma'], 0)
        
        result = self.bs.calculate(100, 100, 0.25, 0.20, 'put')
        self.assertGreater(result['gamma'], 0)
    
    def test_vega_positive(self):
        """Test that vega is always positive"""
        result = self.bs.calculate(100, 100, 0.25, 0.20, 'call')
        self.assertGreater(result['vega'], 0)
        
        result = self.bs.calculate(100, 100, 0.25, 0.20, 'put')
        self.assertGreater(result['vega'], 0)
    
    def test_theta_negative(self):
        """Test that theta is negative (time decay)"""
        result = self.bs.calculate(100, 100, 0.25, 0.20, 'call')
        self.assertLess(result['theta'], 0)
        
        result = self.bs.calculate(100, 100, 0.25, 0.20, 'put')
        self.assertLess(result['theta'], 0)
    
    def test_second_order_greeks(self):
        """Test second-order Greeks are calculated"""
        result = self.bs.calculate(100, 100, 0.25, 0.20, 'call')
        
        # Check all second-order Greeks exist
        self.assertIn('vanna', result)
        self.assertIn('vomma', result)
        self.assertIn('charm', result)
        self.assertIn('speed', result)
        
        # Check they're finite numbers
        self.assertTrue(np.isfinite(result['vanna']))
        self.assertTrue(np.isfinite(result['vomma']))
        self.assertTrue(np.isfinite(result['charm']))
        self.assertTrue(np.isfinite(result['speed']))
    
    def test_expired_option(self):
        """Test expired option returns zero values"""
        result = self.bs.calculate(100, 100, 0.0, 0.20, 'call')
        self.assertEqual(result['price'], 0.0)
        self.assertEqual(result['delta'], 0.0)
        self.assertEqual(result['gamma'], 0.0)
    
    def test_implied_volatility(self):
        """Test implied volatility calculation"""
        # Calculate price first
        result = self.bs.calculate(100, 100, 0.25, 0.20, 'call')
        market_price = result['price']
        
        # Calculate IV from price
        iv = self.bs.calculate_implied_volatility(
            market_price, 100, 100, 0.25, 'call'
        )
        
        # Should be close to 0.20
        self.assertIsNotNone(iv)
        self.assertAlmostEqual(iv, 0.20, delta=0.01)
    
    def test_put_call_parity(self):
        """Test put-call parity"""
        S = 100
        K = 100
        T = 0.25
        r = 0.05
        sigma = 0.20
        
        call = self.bs.calculate(S, K, T, sigma, 'call')
        put = self.bs.calculate(S, K, T, sigma, 'put')
        
        # Put-call parity: C - P = S - K*e^(-r*T)
        lhs = call['price'] - put['price']
        rhs = S - K * np.exp(-r * T)
        
        self.assertAlmostEqual(lhs, rhs, delta=0.01)

if __name__ == '__main__':
    unittest.main()

