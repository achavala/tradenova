"""
Options Agent
Trades directional options based on regime and bias
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

from core.agents.base_agent import BaseAgent, TradeIntent, TradeDirection
from core.regime.classifier import RegimeSignal, RegimeType
from services.options_data_feed import OptionsDataFeed
from services.iv_calculator import IVCalculator

logger = logging.getLogger(__name__)

class OptionsAgent(BaseAgent):
    """Agent for directional options trading"""
    
    def __init__(self, options_data_feed: OptionsDataFeed, iv_calculator: IVCalculator):
        """
        Initialize Options Agent
        
        Args:
            options_data_feed: Options data feed service
            iv_calculator: IV calculator service
        """
        super().__init__("OptionsAgent", min_confidence=0.65)
        self.options_feed = options_data_feed
        self.iv_calculator = iv_calculator
        self.min_delta = 0.30  # Minimum delta for directional exposure
        self.max_iv_rank = 80.0  # Maximum IV Rank (avoid expensive premium)
    
    def should_activate(self, regime_signal: RegimeSignal, features: Dict) -> bool:
        """Check if Options Agent should activate"""
        # Activate in any regime with clear bias
        return (
            regime_signal.confidence >= 0.4 and
            regime_signal.bias.value != "NEUTRAL"
        )
    
    def evaluate(self, symbol: str, regime_signal: RegimeSignal, features: Dict) -> Optional[TradeIntent]:
        """Evaluate options trading opportunity"""
        if not self.should_activate(regime_signal, features):
            return None
        
        try:
            # Get current stock price
            current_price = features.get('current_price', 0)
            if current_price == 0:
                return None
            
            # Get options chain
            options_chain = self.options_feed.get_options_chain(symbol)
            if not options_chain:
                logger.debug(f"No options chain available for {symbol}")
                return None
            
            # Get expiration dates (prefer 0-30 DTE)
            expirations = self.options_feed.get_expiration_dates(symbol)
            if not expirations:
                return None
            
            # Select expiration (0-30 days out)
            target_expiration = self._select_expiration(expirations)
            if not target_expiration:
                return None
            
            # Filter chain by expiration
            filtered_chain = [
                c for c in options_chain
                if c.get('expiration_date') == target_expiration
            ]
            
            if not filtered_chain:
                return None
            
            # Determine direction based on bias
            option_type = 'call' if regime_signal.bias.value == "BULLISH" else 'put'
            
            # Get ATM option
            option_contract = self.options_feed.get_atm_options(
                symbol,
                target_expiration,
                option_type
            )
            
            if not option_contract:
                return None
            
            # Get option quote
            option_symbol = option_contract.get('symbol') or option_contract.get('contract_symbol')
            if not option_symbol:
                return None
            
            quote = self.options_feed.get_option_quote(option_symbol)
            if not quote:
                return None
            
            # Calculate IV metrics
            # Note: IV may need to be extracted from option contract or calculated
            iv = float(option_contract.get('implied_volatility', 0.2))  # Default 20%
            iv_metrics = self.iv_calculator.get_iv_metrics(symbol, iv)
            
            # Check IV Rank filter
            if iv_metrics['iv_rank'] > self.max_iv_rank:
                logger.debug(f"{symbol}: IV Rank too high ({iv_metrics['iv_rank']:.1f}%)")
                return None
            
            # Calculate Greeks (if not available, use Black-Scholes)
            strike = float(option_contract.get('strike_price', current_price))
            expiration_date = datetime.strptime(target_expiration, '%Y-%m-%d')
            days_to_expiry = (expiration_date - datetime.now()).days
            time_to_expiry = days_to_expiry / 365.0
            
            greeks = self.options_feed.calculate_greeks_black_scholes(
                spot_price=current_price,
                strike=strike,
                time_to_expiry=time_to_expiry,
                risk_free_rate=0.05,  # 5% risk-free rate
                volatility=iv,
                option_type=option_type
            )
            
            # Check delta filter
            if abs(greeks['delta']) < self.min_delta:
                logger.debug(f"{symbol}: Delta too low ({greeks['delta']:.2f})")
                return None
            
            # Calculate confidence
            confidence = 0.6
            reasoning_parts = []
            
            # Regime confidence
            confidence += regime_signal.confidence * 0.2
            reasoning_parts.append(f"{regime_signal.regime_type.value} regime")
            
            # IV Rank adjustment (lower is better for buying)
            if iv_metrics['iv_rank'] < 50:
                confidence += 0.1
                reasoning_parts.append(f"Low IV Rank ({iv_metrics['iv_rank']:.1f}%)")
            
            # Delta strength
            if abs(greeks['delta']) > 0.50:
                confidence += 0.1
                reasoning_parts.append(f"Strong delta ({greeks['delta']:.2f})")
            
            confidence = min(1.0, confidence)
            
            if confidence < self.min_confidence:
                return None
            
            # Position sizing (2% max for options)
            position_size = min(0.02, confidence * 0.02)
            
            # Create options trade intent
            # Note: This is a simplified version - in production, you'd want
            # to return an OptionsTradeIntent with strike, expiration, etc.
            
            return TradeIntent(
                direction=TradeDirection.LONG if option_type == 'call' else TradeDirection.SHORT,
                confidence=confidence,
                position_size_suggestion=position_size,
                reasoning=f"Options {option_type.upper()}: " + " | ".join(reasoning_parts),
                agent_name=self.name,
                symbol=option_symbol,  # Option symbol, not underlying
                entry_price=quote.get('last') or quote.get('ask', 0),
                stop_loss=None,  # Options stop loss handled differently
                take_profit=None  # Options take profit handled differently
            )
            
        except Exception as e:
            logger.error(f"Error in OptionsAgent for {symbol}: {e}")
            return None
    
    def _select_expiration(self, expirations: list, target_dte: int = 15) -> Optional[str]:
        """
        Select expiration date closest to target DTE (0-30 days)
        
        Args:
            expirations: List of expiration dates (YYYY-MM-DD)
            target_dte: Target days to expiration (default: 15)
            
        Returns:
            Selected expiration date or None
        """
        if not expirations:
            return None
        
        today = datetime.now().date()
        best_expiration = None
        best_diff = float('inf')
        
        for exp_date_str in expirations:
            try:
                exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                dte = (exp_date - today).days
                
                # Prefer 0-30 DTE (user requirement)
                if 0 <= dte <= 30:
                    diff = abs(dte - target_dte)
                    if diff < best_diff:
                        best_diff = diff
                        best_expiration = exp_date_str
            except:
                continue
        
        # If no 0-30 DTE found, use closest within range
        if not best_expiration:
            today = datetime.now().date()
            for exp_date_str in expirations:
                try:
                    exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                    dte = (exp_date - today).days
                    if 0 <= dte <= 30:  # Must be 0-30 DTE
                        diff = abs(dte - target_dte)
                        if diff < best_diff:
                            best_diff = diff
                            best_expiration = exp_date_str
                except:
                    continue
        
        return best_expiration

