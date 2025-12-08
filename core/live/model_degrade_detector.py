"""
Model Degrade Detection System
Monitors RL model performance and automatically disables if degrading
"""
import logging
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

class ModelDegradeDetector:
    """Detects when RL model performance degrades"""
    
    def __init__(
        self,
        loss_threshold: float = 0.15,  # 15% loss threshold
        accuracy_window: int = 20,  # Last 20 predictions
        min_accuracy: float = 0.45,  # Minimum 45% accuracy
        entropy_threshold: float = 0.8,  # High entropy = uncertain
        volatility_mismatch_threshold: float = 0.3  # 30% mismatch
    ):
        """
        Initialize degrade detector
        
        Args:
            loss_threshold: Maximum allowed loss before disable
            accuracy_window: Number of predictions to track
            min_accuracy: Minimum accuracy to maintain
            entropy_threshold: Maximum prediction entropy
            volatility_mismatch_threshold: Max volatility mismatch
        """
        self.loss_threshold = loss_threshold
        self.accuracy_window = accuracy_window
        self.min_accuracy = min_accuracy
        self.entropy_threshold = entropy_threshold
        self.volatility_mismatch_threshold = volatility_mismatch_threshold
        
        # Tracking
        self.predictions: deque = deque(maxlen=accuracy_window)
        self.outcomes: deque = deque(maxlen=accuracy_window)
        self.confidences: deque = deque(maxlen=accuracy_window)
        self.regime_history: deque = deque(maxlen=10)
        
        # Performance metrics
        self.total_loss = 0.0
        self.total_trades = 0
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        
        # Status
        self.is_degraded = False
        self.degrade_reason = None
        self.last_check = None
        
    def record_prediction(
        self,
        prediction: Dict,
        actual_outcome: Optional[float] = None,
        pnl: Optional[float] = None
    ):
        """
        Record a prediction and its outcome
        
        Args:
            prediction: Prediction dictionary with direction, confidence, etc.
            actual_outcome: Actual price movement (optional)
            pnl: P&L from trade (optional)
        """
        self.predictions.append(prediction)
        self.confidences.append(prediction.get('confidence', 0.5))
        
        if actual_outcome is not None:
            self.outcomes.append(actual_outcome)
        
        if pnl is not None:
            self.total_trades += 1
            self.total_loss += abs(min(0, pnl))  # Only count losses
            
            if pnl < 0:
                self.consecutive_losses += 1
                self.max_consecutive_losses = max(
                    self.max_consecutive_losses,
                    self.consecutive_losses
                )
            else:
                self.consecutive_losses = 0
        
        # Record regime
        if 'regime' in prediction:
            self.regime_history.append(prediction['regime'])
    
    def check_degradation(self) -> tuple:
        """
        Check if model is degrading
        
        Returns:
            (is_degraded, reason)
        """
        self.last_check = datetime.now()
        
        # Check 1: Loss threshold
        if self.total_trades > 0:
            avg_loss = self.total_loss / self.total_trades
            if avg_loss > self.loss_threshold:
                self.is_degraded = True
                self.degrade_reason = f"Average loss {avg_loss:.2%} exceeds threshold {self.loss_threshold:.2%}"
                logger.warning(f"Model degraded: {self.degrade_reason}")
                return True, self.degrade_reason
        
        # Check 2: Exponentially weighted rolling accuracy
        if len(self.outcomes) >= self.accuracy_window:
            # Use exponential weighting (more recent predictions weighted higher)
            weights = np.exp(np.linspace(-1, 0, len(self.outcomes)))
            weights = weights / weights.sum()
            
            correct = []
            for p, o in zip(self.predictions, self.outcomes):
                is_correct = (
                    (p['direction'] == 'LONG' and o > 0) or
                    (p['direction'] == 'SHORT' and o < 0) or
                    (p['direction'] == 'FLAT')
                )
                correct.append(1.0 if is_correct else 0.0)
            
            # Weighted accuracy
            accuracy = np.average(correct, weights=weights)
            
            if accuracy < self.min_accuracy:
                self.is_degraded = True
                self.degrade_reason = f"Accuracy {accuracy:.2%} below minimum {self.min_accuracy:.2%}"
                logger.warning(f"Model degraded: {self.degrade_reason}")
                return True, self.degrade_reason
        
        # Check 3: Prediction entropy (uncertainty)
        if len(self.confidences) >= 10:
            avg_confidence = np.mean(list(self.confidences))
            entropy = 1.0 - avg_confidence  # Higher entropy = lower confidence
            
            if entropy > self.entropy_threshold:
                self.is_degraded = True
                self.degrade_reason = f"Prediction entropy {entropy:.2f} exceeds threshold {self.entropy_threshold:.2f}"
                logger.warning(f"Model degraded: {self.degrade_reason}")
                return True, self.degrade_reason
        
        # Check 4: Consecutive losses
        if self.consecutive_losses >= 5:
            self.is_degraded = True
            self.degrade_reason = f"{self.consecutive_losses} consecutive losses"
            logger.warning(f"Model degraded: {self.degrade_reason}")
            return True, self.degrade_reason
        
        # Check 5: Volatility regime mismatch
        if len(self.regime_history) >= 5:
            # Check if model is making predictions in wrong volatility regime
            recent_regimes = list(self.regime_history)[-5:]
            regime_changes = sum(1 for i in range(1, len(recent_regimes))
                               if recent_regimes[i] != recent_regimes[i-1])
            
            if regime_changes / len(recent_regimes) > self.volatility_mismatch_threshold:
                self.is_degraded = True
                self.degrade_reason = f"High regime volatility ({regime_changes} changes in {len(recent_regimes)} predictions)"
                logger.warning(f"Model degraded: {self.degrade_reason}")
                return True, self.degrade_reason
        
        # Model is healthy
        if self.is_degraded:
            logger.info("Model performance recovered - re-enabling")
        self.is_degraded = False
        self.degrade_reason = None
        return False, None
    
    def get_status(self) -> Dict:
        """Get current status"""
        accuracy = None
        if len(self.outcomes) > 0:
            correct = sum(1 for p, o in zip(self.predictions, self.outcomes)
                         if (p['direction'] == 'LONG' and o > 0) or
                            (p['direction'] == 'SHORT' and o < 0))
            accuracy = correct / len(self.outcomes)
        
        avg_confidence = np.mean(list(self.confidences)) if self.confidences else 0.5
        entropy = 1.0 - avg_confidence
        
        return {
            'is_degraded': self.is_degraded,
            'degrade_reason': self.degrade_reason,
            'accuracy': accuracy,
            'avg_confidence': avg_confidence,
            'entropy': entropy,
            'total_trades': self.total_trades,
            'consecutive_losses': self.consecutive_losses,
            'avg_loss': self.total_loss / self.total_trades if self.total_trades > 0 else 0.0,
            'last_check': self.last_check.isoformat() if self.last_check else None
        }
    
    def reset(self):
        """Reset detector (e.g., after model retraining)"""
        self.predictions.clear()
        self.outcomes.clear()
        self.confidences.clear()
        self.regime_history.clear()
        self.total_loss = 0.0
        self.total_trades = 0
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        self.is_degraded = False
        self.degrade_reason = None
        logger.info("Model degrade detector reset")

