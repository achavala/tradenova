"""
Mean Reversion Agent
Activates in MEAN_REVERSION regime, trades range-bound markets
"""
import logging
from typing import Dict, Optional

from core.agents.base_agent import BaseAgent, TradeIntent, TradeDirection
from core.regime.classifier import RegimeSignal, RegimeType

logger = logging.getLogger(__name__)

class MeanReversionAgent(BaseAgent):
    """Agent for mean-reversion strategies"""
    
    def __init__(self):
        """Initialize Mean Reversion Agent"""
        super().__init__("MeanReversionAgent", min_confidence=0.6)
    
    def should_activate(self, regime_signal: RegimeSignal, features: Dict) -> bool:
        """Check if Mean Reversion Agent should activate"""
        return (
            regime_signal.regime_type == RegimeType.MEAN_REVERSION and
            regime_signal.confidence >= 0.4
        )
    
    def evaluate(self, symbol: str, regime_signal: RegimeSignal, features: Dict) -> Optional[TradeIntent]:
        """Evaluate mean-reversion opportunity"""
        if not self.should_activate(regime_signal, features):
            return None
        
        current_price = features.get('current_price', 0)
        ema_9 = features.get('ema_9', 0)
        rsi = features.get('rsi', 50)
        vwap = features.get('vwap', 0)
        vwap_deviation = features.get('vwap_deviation', 0)
        fvg = features.get('fvg')
        
        if current_price == 0:
            return None
        
        confidence = 0.5
        direction = TradeDirection.FLAT
        reasoning_parts = []
        
        # RSI extremes
        if rsi < 30:  # Oversold
            direction = TradeDirection.LONG
            confidence += 0.25
            reasoning_parts.append(f"Oversold (RSI: {rsi:.1f})")
        elif rsi > 70:  # Overbought
            direction = TradeDirection.SHORT
            confidence += 0.25
            reasoning_parts.append(f"Overbought (RSI: {rsi:.1f})")
        
        # Price near EMA9 (mean reversion entry)
        if ema_9 > 0:
            price_to_ema = abs(current_price - ema_9) / ema_9
            if price_to_ema < 0.01:  # Within 1%
                confidence += 0.15
                reasoning_parts.append("Price near EMA9")
        
        # VWAP deviation
        if abs(vwap_deviation) > 2.0:  # Significant deviation
            if vwap_deviation < -2.0:  # Below VWAP
                if direction == TradeDirection.FLAT:
                    direction = TradeDirection.LONG
                confidence += 0.15
                reasoning_parts.append("Price below VWAP")
            elif vwap_deviation > 2.0:  # Above VWAP
                if direction == TradeDirection.FLAT:
                    direction = TradeDirection.SHORT
                confidence += 0.15
                reasoning_parts.append("Price above VWAP")
        
        # FVG fill opportunity
        if fvg and not fvg.get('filled', True):
            fvg_distance = abs(fvg.get('distance_pct', 100))
            if fvg_distance < 1.0:  # Close to FVG midpoint
                confidence += 0.2
                reasoning_parts.append(f"FVG fill opportunity ({fvg['type']})")
                
                # Adjust direction based on FVG type
                if fvg['type'] == 'bullish' and direction == TradeDirection.FLAT:
                    direction = TradeDirection.LONG
                elif fvg['type'] == 'bearish' and direction == TradeDirection.FLAT:
                    direction = TradeDirection.SHORT
        
        # Cap confidence
        confidence = min(1.0, confidence)
        
        if direction == TradeDirection.FLAT or confidence < self.min_confidence:
            return None
        
        # Position sizing (3% max for mean reversion)
        position_size = min(0.03, confidence * 0.03)
        
        # Calculate stop loss and take profit
        stop_loss = None
        take_profit = None
        atr = features.get('atr', current_price * 0.02)
        
        if direction == TradeDirection.LONG:
            stop_loss = current_price - (atr * 1.0)
            take_profit = current_price + (atr * 2.0)
        else:
            stop_loss = current_price + (atr * 1.0)
            take_profit = current_price - (atr * 2.0)
        
        return TradeIntent(
            direction=direction,
            confidence=confidence,
            position_size_suggestion=position_size,
            reasoning=" | ".join(reasoning_parts) if reasoning_parts else "Mean reversion signal",
            agent_name=self.name,
            symbol=symbol,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

