"""
Volatility Agent
Trades volatility expansion/compression
"""
import logging
from typing import Dict, Optional

from core.agents.base_agent import BaseAgent, TradeIntent, TradeDirection
from core.regime.classifier import RegimeSignal, RegimeType, VolatilityLevel

logger = logging.getLogger(__name__)

class VolatilityAgent(BaseAgent):
    """Agent for volatility-based strategies"""
    
    def __init__(self):
        """Initialize Volatility Agent"""
        super().__init__("VolatilityAgent", min_confidence=0.65)
    
    def should_activate(self, regime_signal: RegimeSignal, features: Dict) -> bool:
        """Check if Volatility Agent should activate"""
        return (
            regime_signal.regime_type == RegimeType.EXPANSION and
            regime_signal.confidence >= 0.4
        )
    
    def evaluate(self, symbol: str, regime_signal: RegimeSignal, features: Dict) -> Optional[TradeIntent]:
        """Evaluate volatility trading opportunity"""
        if not self.should_activate(regime_signal, features):
            return None
        
        atr_pct = features.get('atr_pct', 0)
        current_price = features.get('current_price', 0)
        trend_direction = regime_signal.trend_direction
        
        if current_price == 0:
            return None
        
        # Volatility expansion - trade in direction of trend
        if atr_pct > 2.0:  # High volatility
            confidence = 0.7
            direction = TradeDirection.FLAT
            
            if trend_direction.value == "UP":
                direction = TradeDirection.LONG
                reasoning = f"Volatility expansion in uptrend (ATR: {atr_pct:.2f}%)"
            elif trend_direction.value == "DOWN":
                direction = TradeDirection.SHORT
                reasoning = f"Volatility expansion in downtrend (ATR: {atr_pct:.2f}%)"
            else:
                return None  # No clear direction
            
            # Position sizing (4% max for volatility trades)
            position_size = min(0.04, confidence * 0.04)
            
            # Calculate stop loss and take profit
            atr = features.get('atr', current_price * 0.02)
            if direction == TradeDirection.LONG:
                stop_loss = current_price - (atr * 2.0)
                take_profit = current_price + (atr * 4.0)
            else:
                stop_loss = current_price + (atr * 2.0)
                take_profit = current_price - (atr * 4.0)
            
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
        
        return None

