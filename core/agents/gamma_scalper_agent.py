"""
Gamma Scalper Agent
Buys strangles in expansion regime with negative GEX
"""
import logging
from typing import Dict, Optional
from datetime import datetime

from core.agents.base_agent import BaseAgent, TradeIntent, TradeDirection
from core.regime.classifier import RegimeSignal, RegimeType
from services.options_data_feed import OptionsDataFeed
from services.iv_calculator import IVCalculator
from services.gex_calculator import GEXCalculator

logger = logging.getLogger(__name__)

class GammaScalperAgent(BaseAgent):
    """Agent for buying strangles in volatility expansion"""
    
    def __init__(
        self,
        options_data_feed: OptionsDataFeed,
        iv_calculator: IVCalculator,
        gex_calculator: GEXCalculator
    ):
        """
        Initialize Gamma Scalper Agent
        
        Args:
            options_data_feed: Options data feed service
            iv_calculator: IV calculator service
            gex_calculator: GEX calculator service
        """
        super().__init__("GammaScalperAgent", min_confidence=0.70)
        self.options_feed = options_data_feed
        self.iv_calculator = iv_calculator
        self.gex_calculator = gex_calculator
        self.max_iv_rank = 20.0  # Maximum IV Rank (cheap premium)
    
    def should_activate(self, regime_signal: RegimeSignal, features: Dict) -> bool:
        """Check if Gamma Scalper should activate"""
        return (
            regime_signal.regime_type == RegimeType.EXPANSION and
            regime_signal.confidence >= 0.4
        )
    
    def evaluate(self, symbol: str, regime_signal: RegimeSignal, features: Dict) -> Optional[TradeIntent]:
        """Evaluate strangle buying opportunity"""
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
                return None
            
            # Calculate GEX
            gex_data = self.gex_calculator.calculate_gex_proxy(options_chain, current_price)
            
            # Check for negative GEX (volatility expansion likely)
            if gex_data['total_gex'] > -100_000_000:  # Not negative enough
                logger.debug(f"{symbol}: GEX not negative enough")
                return None
            
            # Get OTM options for strangle (10-15% OTM)
            strike_offset = current_price * 0.12  # 12% OTM
            
            call_strike = current_price + strike_offset
            put_strike = current_price - strike_offset
            
            # Find closest strikes
            call_option = self._find_closest_strike(options_chain, call_strike, 'call')
            put_option = self._find_closest_strike(options_chain, put_strike, 'put')
            
            if not call_option or not put_option:
                return None
            
            # Check IV Rank (should be low - cheap premium)
            call_iv = float(call_option.get('implied_volatility', 0.2))
            iv_metrics = self.iv_calculator.get_iv_metrics(symbol, call_iv)
            
            if iv_metrics['iv_rank'] > self.max_iv_rank:
                logger.debug(f"{symbol}: IV Rank too high ({iv_metrics['iv_rank']:.1f}%)")
                return None
            
            # Get quotes
            call_symbol = call_option.get('symbol') or call_option.get('contract_symbol')
            put_symbol = put_option.get('symbol') or put_option.get('contract_symbol')
            
            if not call_symbol or not put_symbol:
                return None
            
            call_quote = self.options_feed.get_option_quote(call_symbol)
            put_quote = self.options_feed.get_option_quote(put_symbol)
            
            if not call_quote or not put_quote:
                return None
            
            # Calculate total premium
            call_premium = call_quote.get('ask', 0) or call_quote.get('last', 0)
            put_premium = put_quote.get('ask', 0) or put_quote.get('last', 0)
            total_premium = call_premium + put_premium
            
            if total_premium == 0:
                return None
            
            # Calculate confidence
            confidence = 0.7
            reasoning_parts = []
            
            # Expansion regime
            confidence += regime_signal.confidence * 0.15
            reasoning_parts.append("Expansion regime")
            
            # Negative GEX
            if gex_data['total_gex'] < -500_000_000:
                confidence += 0.1
                reasoning_parts.append("Strong negative GEX")
            
            # Low IV Rank
            if iv_metrics['iv_rank'] < 15:
                confidence += 0.1
                reasoning_parts.append(f"Low IV Rank ({iv_metrics['iv_rank']:.1f}%)")
            
            confidence = min(1.0, confidence)
            
            if confidence < self.min_confidence:
                return None
            
            # Position sizing (2% max for strangles)
            position_size = min(0.02, confidence * 0.02)
            
            # Note: This returns a simplified intent
            # In production, you'd want a MultiLegOptionsIntent with delta hedging
            
            return TradeIntent(
                direction=TradeDirection.LONG,  # Buying strangle
                confidence=confidence,
                position_size_suggestion=position_size,
                reasoning=f"Strangle buy: " + " | ".join(reasoning_parts),
                agent_name=self.name,
                symbol=f"{symbol}_STRANGLE",  # Special symbol for strangle
                entry_price=total_premium,
                stop_loss=None,
                take_profit=None
            )
            
        except Exception as e:
            logger.error(f"Error in GammaScalperAgent for {symbol}: {e}")
            return None
    
    def _find_closest_strike(
        self, 
        options_chain: list, 
        target_strike: float, 
        option_type: str
    ) -> Optional[Dict]:
        """Find option contract closest to target strike"""
        filtered = [
            c for c in options_chain
            if c.get('type', '').lower() == option_type.lower()
        ]
        
        if not filtered:
            return None
        
        closest = min(
            filtered,
            key=lambda x: abs(float(x.get('strike_price', 0)) - target_strike)
        )
        
        return closest

