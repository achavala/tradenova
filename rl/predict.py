"""
RL Prediction Engine
Loads trained models and generates trading predictions
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from pathlib import Path
import os

from rl.trading_environment import TradingEnvironment
from rl.ppo_agent import PPOAgent
from rl.grpo_agent import GRPOAgent
from core.features.indicators import FeatureEngine
from core.regime.classifier import RegimeClassifier

logger = logging.getLogger(__name__)

class RLPredictor:
    """RL-based prediction engine"""
    
    def __init__(
        self,
        model_path: str,
        agent_type: str = 'grpo',
        smoothing_alpha: float = 0.3,
        min_confidence: float = 0.6
    ):
        """
        Initialize RL predictor
        
        Args:
            model_path: Path to trained model
            agent_type: 'ppo' or 'grpo'
            smoothing_alpha: EMA smoothing factor (0-1)
            min_confidence: Minimum confidence to generate signal
        """
        self.model_path = model_path
        self.agent_type = agent_type
        self.smoothing_alpha = smoothing_alpha
        self.min_confidence = min_confidence
        
        # State for smoothing
        self.last_prediction = 0.0
        self.prediction_history = []
        
        # Load model (will be loaded when needed)
        self.agent = None
        self.feature_engine = FeatureEngine()
        self.regime_classifier = RegimeClassifier()
        
    def load_model(self, env: Optional[TradingEnvironment] = None):
        """Load trained model"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        # Create dummy environment if not provided
        if env is None:
            dummy_data = pd.DataFrame({
                'open': [100] * 100,
                'high': [101] * 100,
                'low': [99] * 100,
                'close': [100] * 100,
                'volume': [1000] * 100
            })
            env = TradingEnvironment(dummy_data)
        
        if self.agent_type == 'grpo':
            self.agent = GRPOAgent(env, model_path=self.model_path)
        else:
            self.agent = PPOAgent(env, model_path=self.model_path)
        
        logger.info(f"Loaded {self.agent_type.upper()} model from {self.model_path}")
    
    def predict(
        self,
        symbol: str,
        bars: pd.DataFrame,
        current_price: Optional[float] = None
    ) -> Dict:
        """
        Generate prediction for symbol
        
        Args:
            symbol: Trading symbol
            bars: Historical bars (OHLCV)
            current_price: Current price (optional, will use last close if not provided)
            
        Returns:
            Prediction dictionary with action, confidence, direction, etc.
        """
        if self.agent is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        if bars.empty or len(bars) < 50:
            return {
                'action': 0.0,
                'direction': 'FLAT',
                'confidence': 0.0,
                'reason': 'Insufficient data'
            }
        
        try:
            # Calculate features
            features = self.feature_engine.calculate_all_features(bars)
            if not features:
                return {
                    'action': 0.0,
                    'direction': 'FLAT',
                    'confidence': 0.0,
                    'reason': 'Feature calculation failed'
                }
            
            # Add current price
            if current_price is None:
                current_price = bars['close'].iloc[-1]
            features['current_price'] = current_price
            
            # Classify regime
            regime = self.regime_classifier.classify(features)
            
            # Get observation
            env = TradingEnvironment(bars, initial_balance=10000.0)
            observation = env._get_observation()
            
            # Get prediction from model
            action, _ = self.agent.predict(observation, deterministic=True)
            raw_action = float(action[0])
            
            # Apply smoothing
            smoothed_action = self._smooth_prediction(raw_action)
            
            # Determine direction and confidence
            direction, confidence = self._interpret_action(smoothed_action)
            
            # Apply confidence weighting based on regime
            confidence = self._adjust_confidence(confidence, regime, features)
            
            # Generate prediction
            prediction = {
                'symbol': symbol,
                'raw_action': raw_action,
                'smoothed_action': smoothed_action,
                'direction': direction,
                'confidence': confidence,
                'regime': regime.regime_type.value,
                'regime_confidence': regime.confidence,
                'action_value': smoothed_action,
                'reason': f"RL {self.agent_type.upper()} prediction in {regime.regime_type.value} regime"
            }
            
            # Only return signal if confidence is high enough
            if confidence < self.min_confidence:
                prediction['direction'] = 'FLAT'
                prediction['reason'] += f" (confidence {confidence:.2%} below threshold {self.min_confidence:.2%})"
            
            self.prediction_history.append(prediction)
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error generating prediction for {symbol}: {e}")
            return {
                'action': 0.0,
                'direction': 'FLAT',
                'confidence': 0.0,
                'reason': f'Prediction error: {str(e)}'
            }
    
    def _smooth_prediction(self, action: float) -> float:
        """Apply EMA smoothing to predictions"""
        if len(self.prediction_history) == 0:
            self.last_prediction = action
        else:
            # EMA smoothing
            self.last_prediction = (
                self.smoothing_alpha * action + 
                (1 - self.smoothing_alpha) * self.last_prediction
            )
        
        return self.last_prediction
    
    def _interpret_action(self, action: float) -> Tuple[str, float]:
        """
        Interpret action value to direction and confidence
        
        Args:
            action: Action value [-1, 1]
            
        Returns:
            (direction, confidence)
        """
        abs_action = abs(action)
        
        # Determine direction
        if action < -0.3:
            direction = 'SHORT'  # BUY PUT
        elif action > 0.3:
            direction = 'LONG'  # BUY CALL
        else:
            direction = 'FLAT'
        
        # Calculate confidence from action magnitude
        # Map [-1, 1] to [0, 1] confidence
        if direction == 'FLAT':
            confidence = 0.5  # Neutral confidence
        else:
            # Confidence increases with distance from 0
            # Action of 0.3 = 0.5 confidence, action of 1.0 = 1.0 confidence
            confidence = 0.5 + (abs_action - 0.3) * (0.5 / 0.7)  # Scale 0.3-1.0 to 0.5-1.0
            confidence = max(0.5, min(1.0, confidence))
        
        return direction, confidence
    
    def _adjust_confidence(
        self,
        base_confidence: float,
        regime: 'RegimeSignal',
        features: Dict
    ) -> float:
        """Adjust confidence based on regime and features"""
        adjusted = base_confidence
        
        # Boost confidence if regime is clear
        if regime.confidence > 0.7:
            adjusted += 0.1
        elif regime.confidence < 0.4:
            adjusted -= 0.2  # Reduce confidence in uncertain regimes
        
        # Adjust based on volatility
        atr_pct = features.get('atr_pct', 2.0)
        if atr_pct > 3.0:  # High volatility
            adjusted -= 0.1  # Reduce confidence in high volatility
        elif atr_pct < 1.0:  # Low volatility
            adjusted += 0.05  # Slight boost in low volatility
        
        # Adjust based on trend strength
        adx = features.get('adx', 20)
        if adx > 25:  # Strong trend
            adjusted += 0.05
        elif adx < 15:  # Weak trend
            adjusted -= 0.05
        
        return max(0.0, min(1.0, adjusted))
    
    def get_prediction_history(self, n: int = 10) -> list:
        """Get last N predictions"""
        return self.prediction_history[-n:] if len(self.prediction_history) > n else self.prediction_history

