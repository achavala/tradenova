"""
EMA Agent
Simple EMA momentum trading (especially for SPY)
"""
import logging
from typing import Dict, Optional

from core.agents.base_agent import BaseAgent, TradeIntent, TradeDirection
from core.regime.classifier import RegimeSignal

logger = logging.getLogger(__name__)

class EMAAgent(BaseAgent):
    """Agent for simple EMA momentum trading"""
    
    def __init__(self, symbol_filter: str = "SPY"):
        """
        Initialize EMA Agent
        
        Args:
            symbol_filter: Only trade this symbol (default: SPY)
        """
        super().__init__("EMAAgent", min_confidence=0.6)
        self.symbol_filter = symbol_filter
    
    def should_activate(self, regime_signal: RegimeSignal, features: Dict) -> bool:
        """Check if EMA Agent should activate"""
        return True  # Always available, but only for specific symbols
    
    def evaluate(self, symbol: str, regime_signal: RegimeSignal, features: Dict) -> Optional[TradeIntent]:
        """Evaluate EMA momentum opportunity"""
        # Only trade specified symbol
        if symbol != self.symbol_filter:
            return None
        
        ema_9 = features.get('ema_9', 0)
        current_price = features.get('current_price', 0)
        
        if current_price == 0 or ema_9 == 0:
            return None
        
        confidence = 0.6
        direction = TradeDirection.FLAT
        
        # Price above EMA9 = bullish
        if current_price > ema_9:
            direction = TradeDirection.LONG
            confidence += 0.2
            reasoning = f"Price above EMA9 ({current_price:.2f} > {ema_9:.2f})"
        # Price below EMA9 = bearish
        elif current_price < ema_9:
            direction = TradeDirection.SHORT
            confidence += 0.2
            reasoning = f"Price below EMA9 ({current_price:.2f} < {ema_9:.2f})"
        else:
            return None
        
        if confidence < self.min_confidence:
            return None
        
        # Position sizing (3% max)
        position_size = min(0.03, confidence * 0.03)
        
        # Calculate stop loss and take profit
        atr = features.get('atr', current_price * 0.02)
        if direction == TradeDirection.LONG:
            stop_loss = current_price - (atr * 1.5)
            take_profit = current_price + (atr * 2.5)
        else:
            stop_loss = current_price + (atr * 1.5)
            take_profit = current_price - (atr * 2.5)
        
        return TradeIntent(
            direction=direction,
            confidence=confidence,
            position_size_suggestion=position_size,
            reasoning=reasoning,
            agent_name=self.name,
            symbol=symbol,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

