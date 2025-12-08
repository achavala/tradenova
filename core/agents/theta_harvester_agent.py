"""
Theta Harvester Agent
Sells straddles in compression regime with high IV
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

class ThetaHarvesterAgent(BaseAgent):
    """Agent for selling straddles to collect theta"""
    
    def __init__(
        self, 
        options_data_feed: OptionsDataFeed,
        iv_calculator: IVCalculator,
        gex_calculator: GEXCalculator
    ):
        """
        Initialize Theta Harvester Agent
        
        Args:
            options_data_feed: Options data feed service
            iv_calculator: IV calculator service
            gex_calculator: GEX calculator service
        """
        super().__init__("ThetaHarvesterAgent", min_confidence=0.70)
        self.options_feed = options_data_feed
        self.iv_calculator = iv_calculator
        self.gex_calculator = gex_calculator
        self.min_iv_rank = 60.0  # Minimum IV Rank (expensive premium)
    
    def should_activate(self, regime_signal: RegimeSignal, features: Dict) -> bool:
        """Check if Theta Harvester should activate"""
        return (
            regime_signal.regime_type == RegimeType.COMPRESSION and
            regime_signal.confidence >= 0.4
        )
    
    def evaluate(self, symbol: str, regime_signal: RegimeSignal, features: Dict) -> Optional[TradeIntent]:
        """Evaluate straddle selling opportunity"""
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
            
            # Check GEX (avoid high negative GEX - volatility expansion risk)
            if gex_data['total_gex'] < -500_000_000:  # Very negative GEX
                logger.debug(f"{symbol}: Negative GEX too high (volatility risk)")
                return None
            
            # Get ATM options for straddle
            call_option = self.options_feed.get_atm_options(symbol, option_type='call')
            put_option = self.options_feed.get_atm_options(symbol, option_type='put')
            
            if not call_option or not put_option:
                return None
            
            # Check IV Rank
            # Use call IV as proxy
            call_iv = float(call_option.get('implied_volatility', 0.2))
            iv_metrics = self.iv_calculator.get_iv_metrics(symbol, call_iv)
            
            if iv_metrics['iv_rank'] < self.min_iv_rank:
                logger.debug(f"{symbol}: IV Rank too low ({iv_metrics['iv_rank']:.1f}%)")
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
            
            # Compression regime
            confidence += regime_signal.confidence * 0.15
            reasoning_parts.append("Compression regime")
            
            # High IV Rank
            if iv_metrics['iv_rank'] > 70:
                confidence += 0.1
                reasoning_parts.append(f"High IV Rank ({iv_metrics['iv_rank']:.1f}%)")
            
            # Low GEX (not too negative)
            if gex_data['total_gex'] > -100_000_000:
                confidence += 0.05
                reasoning_parts.append("Low volatility risk")
            
            confidence = min(1.0, confidence)
            
            if confidence < self.min_confidence:
                return None
            
            # Position sizing (1.5% max for straddles)
            position_size = min(0.015, confidence * 0.015)
            
            # Note: This returns a simplified intent
            # In production, you'd want a MultiLegOptionsIntent
            # For now, we'll use the call option as the primary symbol
            
            return TradeIntent(
                direction=TradeDirection.SHORT,  # Selling straddle
                confidence=confidence,
                position_size_suggestion=position_size,
                reasoning=f"Straddle sell: " + " | ".join(reasoning_parts),
                agent_name=self.name,
                symbol=f"{symbol}_STRADDLE",  # Special symbol for straddle
                entry_price=total_premium,
                stop_loss=None,
                take_profit=None
            )
            
        except Exception as e:
            logger.error(f"Error in ThetaHarvesterAgent for {symbol}: {e}")
            return None

