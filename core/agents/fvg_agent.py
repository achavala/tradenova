"""
FVG (Fair Value Gap) Agent
Trades gap fill opportunities
"""
import logging
from typing import Dict, Optional

from core.agents.base_agent import BaseAgent, TradeIntent, TradeDirection
from core.regime.classifier import RegimeSignal

logger = logging.getLogger(__name__)

class FVGAgent(BaseAgent):
    """Agent for Fair Value Gap fill trades"""
    
    def __init__(self):
        """Initialize FVG Agent"""
        super().__init__("FVGAgent", min_confidence=0.65)
    
    def should_activate(self, regime_signal: RegimeSignal, features: Dict) -> bool:
        """Check if FVG Agent should activate"""
        fvg = features.get('fvg')
        return fvg is not None and not fvg.get('filled', True)
    
    def evaluate(self, symbol: str, regime_signal: RegimeSignal, features: Dict) -> Optional[TradeIntent]:
        """Evaluate FVG fill opportunity"""
        if not self.should_activate(regime_signal, features):
            return None
        
        fvg = features.get('fvg')
        current_price = features.get('current_price', 0)
        
        if not fvg or current_price == 0:
            return None
        
        fvg_type = fvg.get('type')
        midpoint = fvg.get('midpoint', 0)
        distance_pct = fvg.get('distance_pct', 100)
        
        if midpoint == 0:
            return None
        
        # Calculate distance to midpoint
        distance_to_midpoint = abs(current_price - midpoint) / midpoint * 100
        
        # Only trade if close to midpoint (within 2%)
        if distance_to_midpoint > 2.0:
            return None
        
        confidence = 0.7
        direction = TradeDirection.FLAT
        reasoning_parts = []
        
        # Determine direction based on FVG type
        if fvg_type == 'bullish':
            # Price should fill gap upward
            if current_price < midpoint:
                direction = TradeDirection.LONG
                confidence += 0.15
                reasoning_parts.append("Bullish FVG - price below midpoint")
        elif fvg_type == 'bearish':
            # Price should fill gap downward
            if current_price > midpoint:
                direction = TradeDirection.SHORT
                confidence += 0.15
                reasoning_parts.append("Bearish FVG - price above midpoint")
        
        # Adjust confidence based on distance
        if distance_to_midpoint < 0.5:
            confidence += 0.1
            reasoning_parts.append("Very close to FVG midpoint")
        elif distance_to_midpoint < 1.0:
            confidence += 0.05
            reasoning_parts.append("Close to FVG midpoint")
        
        # Cap confidence
        confidence = min(1.0, confidence)
        
        if direction == TradeDirection.FLAT or confidence < self.min_confidence:
            return None
        
        # Position sizing (3% max for FVG trades)
        position_size = min(0.03, confidence * 0.03)
        
        # Calculate stop loss and take profit
        stop_loss = None
        take_profit = None
        atr = features.get('atr', current_price * 0.02)
        
        if direction == TradeDirection.LONG:
            stop_loss = current_price - (atr * 1.0)
            take_profit = midpoint + (atr * 0.5)  # Target just above midpoint
        else:
            stop_loss = current_price + (atr * 1.0)
            take_profit = midpoint - (atr * 0.5)  # Target just below midpoint
        
        return TradeIntent(
            direction=direction,
            confidence=confidence,
            position_size_suggestion=position_size,
            reasoning=" | ".join(reasoning_parts) if reasoning_parts else f"FVG {fvg_type} fill",
            agent_name=self.name,
            symbol=symbol,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

