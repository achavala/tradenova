"""
Ensemble Predictor
Combines multiple prediction sources with weighted voting
"""
import logging
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

class EnsemblePredictor:
    """Combines multiple prediction sources"""
    
    def __init__(
        self,
        rl_weight: float = 0.4,
        trend_weight: float = 0.25,
        volatility_weight: float = 0.15,
        mean_reversion_weight: float = 0.20
    ):
        """
        Initialize ensemble predictor
        
        Args:
            rl_weight: Weight for RL predictions
            trend_weight: Weight for trend-based predictions
            volatility_weight: Weight for volatility-based predictions
            mean_reversion_weight: Weight for mean-reversion predictions
        """
        # Normalize weights
        total = rl_weight + trend_weight + volatility_weight + mean_reversion_weight
        self.rl_weight = rl_weight / total
        self.trend_weight = trend_weight / total
        self.volatility_weight = volatility_weight / total
        self.mean_reversion_weight = mean_reversion_weight / total
        
        logger.info(f"Ensemble weights: RL={self.rl_weight:.2f}, "
                   f"Trend={self.trend_weight:.2f}, "
                   f"Vol={self.volatility_weight:.2f}, "
                   f"MR={self.mean_reversion_weight:.2f}")
    
    def combine_predictions(
        self,
        rl_prediction: Optional[Dict] = None,
        trend_prediction: Optional[Dict] = None,
        volatility_prediction: Optional[Dict] = None,
        mean_reversion_prediction: Optional[Dict] = None
    ) -> Dict:
        """
        Combine multiple predictions into final signal
        
        Args:
            rl_prediction: RL model prediction
            trend_prediction: Trend-based prediction
            volatility_prediction: Volatility-based prediction
            mean_reversion_prediction: Mean-reversion prediction
            
        Returns:
            Combined prediction dictionary
        """
        predictions = []
        weights = []
        sources = []
        
        # Add RL prediction
        if rl_prediction and rl_prediction.get('direction') != 'FLAT':
            predictions.append(self._prediction_to_vector(rl_prediction))
            weights.append(self.rl_weight)
            sources.append('RL')
        
        # Add trend prediction
        if trend_prediction and trend_prediction.get('direction') != 'FLAT':
            predictions.append(self._prediction_to_vector(trend_prediction))
            weights.append(self.trend_weight)
            sources.append('Trend')
        
        # Add volatility prediction
        if volatility_prediction and volatility_prediction.get('direction') != 'FLAT':
            predictions.append(self._prediction_to_vector(volatility_prediction))
            weights.append(self.volatility_weight)
            sources.append('Volatility')
        
        # Add mean-reversion prediction
        if mean_reversion_prediction and mean_reversion_prediction.get('direction') != 'FLAT':
            predictions.append(self._prediction_to_vector(mean_reversion_prediction))
            weights.append(self.mean_reversion_weight)
            sources.append('MeanReversion')
        
        if not predictions:
            return {
                'direction': 'FLAT',
                'confidence': 0.0,
                'reason': 'No predictions available',
                'sources': []
            }
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # Weighted average
        combined_vector = np.average(predictions, axis=0, weights=weights)
        combined_action = combined_vector[0]
        combined_confidence = combined_vector[1]
        
        # Determine direction
        if combined_action < -0.3:
            direction = 'SHORT'
        elif combined_action > 0.3:
            direction = 'LONG'
        else:
            direction = 'FLAT'
        
        # Calculate agreement (how many sources agree)
        agreement = self._calculate_agreement(predictions, direction)
        
        # Apply confidence decay/adjustment based on agreement
        if agreement > 0.7:
            # High agreement - boost confidence
            combined_confidence = min(1.0, combined_confidence * 1.2)
        else:
            # Low agreement - apply decay
            combined_confidence = self.apply_confidence_decay(combined_confidence, agreement)
        
        return {
            'direction': direction,
            'confidence': float(combined_confidence),
            'action': float(combined_action),
            'sources': sources,
            'agreement': agreement,
            'reason': f"Ensemble: {', '.join(sources)} ({agreement:.1%} agreement)"
        }
    
    def _prediction_to_vector(self, prediction: Dict) -> np.ndarray:
        """Convert prediction to vector [action, confidence]"""
        direction = prediction.get('direction', 'FLAT')
        confidence = prediction.get('confidence', 0.5)
        
        if direction == 'LONG':
            action = confidence  # 0.5 to 1.0
        elif direction == 'SHORT':
            action = -confidence  # -0.5 to -1.0
        else:
            action = 0.0
        
        return np.array([action, confidence])
    
    def _calculate_agreement(self, predictions: List[np.ndarray], direction: str) -> float:
        """Calculate how many predictions agree on direction"""
        if not predictions:
            return 0.0
        
        agreed = 0
        for pred in predictions:
            pred_action = pred[0]
            if direction == 'LONG' and pred_action > 0:
                agreed += 1
            elif direction == 'SHORT' and pred_action < 0:
                agreed += 1
            elif direction == 'FLAT' and abs(pred_action) < 0.3:
                agreed += 1
        
        return agreed / len(predictions)
    
    def apply_confidence_decay(self, base_confidence: float, agreement: float) -> float:
        """
        Apply confidence decay when ensemble disagreement is high
        
        Args:
            base_confidence: Base confidence level
            agreement: Agreement ratio (0-1)
            
        Returns:
            Adjusted confidence
        """
        # If agreement is low, reduce confidence
        if agreement < 0.5:
            # High disagreement - reduce confidence significantly
            decay_factor = 0.5 + (agreement * 0.5)  # 0.5 to 1.0
            adjusted = base_confidence * decay_factor
        elif agreement < 0.7:
            # Moderate disagreement - slight reduction
            decay_factor = 0.8 + (agreement - 0.5) * 0.4  # 0.8 to 1.0
            adjusted = base_confidence * decay_factor
        else:
            # High agreement - no decay
            adjusted = base_confidence
        
        return max(0.0, min(1.0, adjusted))

