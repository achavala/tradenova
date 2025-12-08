"""
Trend Agent
Activates in TREND regime, follows momentum
"""
import logging
from typing import Dict, Optional

from core.agents.base_agent import BaseAgent, TradeIntent, TradeDirection
from core.regime.classifier import RegimeSignal, RegimeType, TrendDirection

logger = logging.getLogger(__name__)

class TrendAgent(BaseAgent):
    """Agent for trend-following strategies"""
    
    def __init__(self):
        """Initialize Trend Agent"""
        super().__init__("TrendAgent", min_confidence=0.6)
    
    def should_activate(self, regime_signal: RegimeSignal, features: Dict) -> bool:
        """Check if Trend Agent should activate"""
        return (
            regime_signal.regime_type == RegimeType.TREND and
            regime_signal.confidence >= 0.4
        )
    
    def evaluate(self, symbol: str, regime_signal: RegimeSignal, features: Dict) -> Optional[TradeIntent]:
        """Evaluate trend trading opportunity"""
        if not self.should_activate(regime_signal, features):
            return None
        
        ema_9 = features.get('ema_9', 0)
        ema_21 = features.get('ema_21', 0)
        current_price = features.get('current_price', 0)
        adx = features.get('adx', 0)
        vwap = features.get('vwap', 0)
        vwap_deviation = features.get('vwap_deviation', 0)
        
        if current_price == 0 or ema_9 == 0 or ema_21 == 0:
            return None
        
        confidence = 0.5
        direction = TradeDirection.FLAT
        reasoning_parts = []
        
        # Golden cross (EMA9 > EMA21) - bullish
        if ema_9 > ema_21:
            if current_price > ema_9:
                direction = TradeDirection.LONG
                confidence += 0.2
                reasoning_parts.append("Golden cross with price above EMA9")
            
            if current_price > vwap:
                confidence += 0.15
                reasoning_parts.append("Price above VWAP")
            
            if regime_signal.trend_direction == TrendDirection.UP:
                confidence += 0.15
                reasoning_parts.append("Uptrend confirmed")
        
        # Death cross (EMA9 < EMA21) - bearish
        elif ema_9 < ema_21:
            if current_price < ema_9:
                direction = TradeDirection.SHORT
                confidence += 0.2
                reasoning_parts.append("Death cross with price below EMA9")
            
            if current_price < vwap:
                confidence += 0.15
                reasoning_parts.append("Price below VWAP")
            
            if regime_signal.trend_direction == TrendDirection.DOWN:
                confidence += 0.15
                reasoning_parts.append("Downtrend confirmed")
        
        # ADX strength
        if adx > 25:
            confidence += 0.1
            reasoning_parts.append(f"Strong trend (ADX: {adx:.1f})")
        
        # Cap confidence
        confidence = min(1.0, confidence)
        
        if direction == TradeDirection.FLAT or confidence < self.min_confidence:
            return None
        
        # Position sizing (5% max for trend trades)
        position_size = min(0.05, confidence * 0.05)
        
        # Calculate stop loss and take profit
        stop_loss = None
        take_profit = None
        atr = features.get('atr', current_price * 0.02)
        
        if direction == TradeDirection.LONG:
            stop_loss = current_price - (atr * 1.5)
            take_profit = current_price + (atr * 3.0)
        else:
            stop_loss = current_price + (atr * 1.5)
            take_profit = current_price - (atr * 3.0)
        
        return TradeIntent(
            direction=direction,
            confidence=confidence,
            position_size_suggestion=position_size,
            reasoning=" | ".join(reasoning_parts) if reasoning_parts else "Trend signal",
            agent_name=self.name,
            symbol=symbol,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

