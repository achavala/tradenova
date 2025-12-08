"""
Meta-Policy Controller
Intelligently combines agent signals using multi-armed bandit principles
"""
import logging
from typing import List, Optional, Dict
from core.agents.base_agent import TradeIntent, TradeDirection

logger = logging.getLogger(__name__)

class MetaPolicyController:
    """Meta-policy controller for agent coordination"""
    
    def __init__(self):
        """Initialize meta-policy controller"""
        self.agent_weights: Dict[str, float] = {}
    
    def arbitrate(
        self, 
        intents: List[TradeIntent],
        regime_type: str,
        volatility_level: str
    ) -> Optional[TradeIntent]:
        """
        Arbitrate between multiple agent intents
        
        Args:
            intents: List of trade intents from agents
            regime_type: Current regime type
            volatility_level: Current volatility level
            
        Returns:
            Final trade intent or None
        """
        if not intents:
            return None
        
        # Filter intents
        filtered_intents = self._filter_intents(intents)
        
        if not filtered_intents:
            return None
        
        # Score intents
        scored_intents = self._score_intents(
            filtered_intents, 
            regime_type, 
            volatility_level
        )
        
        if not scored_intents:
            return None
        
        # Find best intent
        best_intent = max(scored_intents, key=lambda x: x['score'])
        
        # Check if scores are close (within 5%)
        if len(scored_intents) > 1:
            scores = [x['score'] for x in scored_intents]
            max_score = max(scores)
            second_max = sorted(scores, reverse=True)[1] if len(scores) > 1 else 0
            
            if abs(max_score - second_max) / max_score < 0.05:
                # Scores are close, blend intents
                return self._blend_intents(scored_intents)
        
        return best_intent['intent']
    
    def _filter_intents(self, intents: List[TradeIntent]) -> List[TradeIntent]:
        """Filter out low-confidence or conflicting intents"""
        filtered = []
        
        # Group by direction
        long_intents = [i for i in intents if i.direction == TradeDirection.LONG]
        short_intents = [i for i in intents if i.direction == TradeDirection.SHORT]
        flat_intents = [i for i in intents if i.direction == TradeDirection.FLAT]
        
        # Remove flat intents
        filtered = [i for i in intents if i.direction != TradeDirection.FLAT]
        
        # Resolve conflicts (if both long and short)
        if long_intents and short_intents:
            # Keep the direction with higher total confidence
            long_confidence = sum(i.confidence for i in long_intents)
            short_confidence = sum(i.confidence for i in short_intents)
            
            if long_confidence > short_confidence:
                filtered = long_intents
            else:
                filtered = short_intents
        
        # Filter by minimum confidence
        filtered = [i for i in filtered if i.confidence >= 0.6]
        
        return filtered
    
    def _score_intents(
        self, 
        intents: List[TradeIntent],
        regime_type: str,
        volatility_level: str
    ) -> List[Dict]:
        """Score intents based on multiple factors"""
        scored = []
        
        for intent in intents:
            # Get agent weight (default to 1.0)
            agent_weight = self.agent_weights.get(intent.agent_name, 1.0)
            
            # Regime weight (how well agent matches regime)
            regime_weight = 1.0  # Simplified for now
            
            # Volatility weight
            volatility_weight = 1.0
            if volatility_level == "HIGH":
                volatility_weight = 0.9  # Slightly reduce in high volatility
            elif volatility_level == "LOW":
                volatility_weight = 1.1  # Slightly increase in low volatility
            
            # Calculate score
            score = (
                agent_weight * 
                regime_weight * 
                volatility_weight * 
                intent.confidence
            )
            
            scored.append({
                'intent': intent,
                'score': score
            })
        
        return scored
    
    def _blend_intents(self, scored_intents: List[Dict]) -> TradeIntent:
        """Blend multiple intents when scores are close"""
        if not scored_intents:
            return None
        
        # Use the highest scoring intent as base
        best = max(scored_intents, key=lambda x: x['score'])
        base_intent = best['intent']
        
        # Average position size from top intents
        top_intents = sorted(scored_intents, key=lambda x: x['score'], reverse=True)[:3]
        avg_position_size = sum(
            x['intent'].position_size_suggestion for x in top_intents
        ) / len(top_intents)
        
        # Create blended intent
        blended = TradeIntent(
            direction=base_intent.direction,
            confidence=base_intent.confidence,
            position_size_suggestion=avg_position_size,
            reasoning=f"Blended: {', '.join(x['intent'].agent_name for x in top_intents)}",
            agent_name="MetaPolicy",
            symbol=base_intent.symbol,
            entry_price=base_intent.entry_price,
            stop_loss=base_intent.stop_loss,
            take_profit=base_intent.take_profit
        )
        
        return blended
    
    def update_agent_weight(self, agent_name: str, fitness: float):
        """Update agent weight based on performance"""
        self.agent_weights[agent_name] = fitness
        logger.info(f"Updated {agent_name} weight to {fitness:.3f}")
    
    def get_agent_weights(self) -> Dict[str, float]:
        """Get current agent weights"""
        return self.agent_weights.copy()

