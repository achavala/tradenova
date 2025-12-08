"""
Regime Classification Engine
Classifies market conditions into distinct regimes
"""
import logging
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class RegimeType(Enum):
    """Market regime types"""
    TREND = "TREND"
    MEAN_REVERSION = "MEAN_REVERSION"
    EXPANSION = "EXPANSION"
    COMPRESSION = "COMPRESSION"

class TrendDirection(Enum):
    """Trend direction"""
    UP = "UP"
    DOWN = "DOWN"
    SIDEWAYS = "SIDEWAYS"

class VolatilityLevel(Enum):
    """Volatility levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Bias(Enum):
    """Market bias"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

@dataclass
class RegimeSignal:
    """Regime classification signal"""
    regime_type: RegimeType
    trend_direction: TrendDirection
    volatility_level: VolatilityLevel
    bias: Bias
    confidence: float  # 0.0 - 1.0
    active_fvg: Optional[Dict] = None

class RegimeClassifier:
    """Classifies market conditions into regimes"""
    
    def __init__(self):
        """Initialize regime classifier"""
        # Thresholds
        self.adx_trend_threshold = 25.0
        self.hurst_mean_reversion_threshold = 0.45
        self.atr_expansion_threshold = 2.0  # % of price
        self.atr_compression_threshold = 0.5  # % of price
        self.rsi_overbought = 70
        self.rsi_oversold = 30
    
    def classify(self, features: Dict) -> RegimeSignal:
        """
        Classify current market regime
        
        Args:
            features: Feature dictionary from FeatureEngine
            
        Returns:
            RegimeSignal with classification
        """
        if not features:
            return self._default_signal()
        
        # Extract key features
        adx = features.get('adx', 0)
        hurst = features.get('hurst', 0.5)
        atr_pct = features.get('atr_pct', 0)
        slope = features.get('slope', 0)
        r_squared = features.get('r_squared', 0)
        ema_9 = features.get('ema_9', 0)
        ema_21 = features.get('ema_21', 0)
        current_price = features.get('current_price', 0)
        vwap_deviation = features.get('vwap_deviation', 0)
        fvg = features.get('fvg')
        
        # Determine trend direction
        trend_direction = self._determine_trend_direction(
            slope, ema_9, ema_21, current_price
        )
        
        # Determine volatility level
        volatility_level = self._determine_volatility_level(atr_pct)
        
        # Determine bias
        bias = self._determine_bias(
            trend_direction, vwap_deviation, features.get('rsi', 50)
        )
        
        # Classify regime
        regime_type, confidence = self._classify_regime(
            adx, hurst, atr_pct, r_squared, slope
        )
        
        return RegimeSignal(
            regime_type=regime_type,
            trend_direction=trend_direction,
            volatility_level=volatility_level,
            bias=bias,
            confidence=confidence,
            active_fvg=fvg if fvg and not fvg.get('filled', True) else None
        )
    
    def _determine_trend_direction(
        self, slope: float, ema_9: float, ema_21: float, current_price: float
    ) -> TrendDirection:
        """Determine trend direction"""
        if ema_9 == 0 or ema_21 == 0:
            return TrendDirection.SIDEWAYS
        
        # EMA crossover
        if ema_9 > ema_21 and slope > 0:
            return TrendDirection.UP
        elif ema_9 < ema_21 and slope < 0:
            return TrendDirection.DOWN
        else:
            return TrendDirection.SIDEWAYS
    
    def _determine_volatility_level(self, atr_pct: float) -> VolatilityLevel:
        """Determine volatility level"""
        if atr_pct < 1.0:
            return VolatilityLevel.LOW
        elif atr_pct < 2.5:
            return VolatilityLevel.MEDIUM
        else:
            return VolatilityLevel.HIGH
    
    def _determine_bias(
        self, trend_direction: TrendDirection, vwap_deviation: float, rsi: float
    ) -> Bias:
        """Determine market bias"""
        bullish_signals = 0
        bearish_signals = 0
        
        # Trend direction
        if trend_direction == TrendDirection.UP:
            bullish_signals += 1
        elif trend_direction == TrendDirection.DOWN:
            bearish_signals += 1
        
        # VWAP deviation
        if vwap_deviation > 1.0:
            bullish_signals += 1
        elif vwap_deviation < -1.0:
            bearish_signals += 1
        
        # RSI
        if rsi > 50:
            bullish_signals += 1
        elif rsi < 50:
            bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            return Bias.BULLISH
        elif bearish_signals > bullish_signals:
            return Bias.BEARISH
        else:
            return Bias.NEUTRAL
    
    def _classify_regime(
        self, adx: float, hurst: float, atr_pct: float, r_squared: float, slope: float
    ) -> tuple:
        """
        Classify regime type and confidence
        
        Returns:
            (RegimeType, confidence)
        """
        scores = {
            RegimeType.TREND: 0.0,
            RegimeType.MEAN_REVERSION: 0.0,
            RegimeType.EXPANSION: 0.0,
            RegimeType.COMPRESSION: 0.0
        }
        
        # TREND regime scoring
        if adx > self.adx_trend_threshold:
            scores[RegimeType.TREND] += 0.4
        if r_squared > 0.7:  # Strong trend quality
            scores[RegimeType.TREND] += 0.3
        if abs(slope) > 0.001:  # Significant slope
            scores[RegimeType.TREND] += 0.2
        
        # MEAN_REVERSION regime scoring
        if hurst < self.hurst_mean_reversion_threshold:
            scores[RegimeType.MEAN_REVERSION] += 0.5
        if r_squared < 0.3:  # Weak trend
            scores[RegimeType.MEAN_REVERSION] += 0.3
        if abs(slope) < 0.0005:  # Flat slope
            scores[RegimeType.MEAN_REVERSION] += 0.2
        
        # EXPANSION regime scoring
        if atr_pct > self.atr_expansion_threshold:
            scores[RegimeType.EXPANSION] += 0.6
        if atr_pct > self.atr_compression_threshold * 2:
            scores[RegimeType.EXPANSION] += 0.3
        
        # COMPRESSION regime scoring
        if atr_pct < self.atr_compression_threshold:
            scores[RegimeType.COMPRESSION] += 0.6
        if atr_pct < self.atr_compression_threshold * 0.5:
            scores[RegimeType.COMPRESSION] += 0.3
        
        # Normalize scores
        total_score = sum(scores.values())
        if total_score > 0:
            for regime in scores:
                scores[regime] /= total_score
        
        # Find best regime
        best_regime = max(scores, key=scores.get)
        confidence = scores[best_regime]
        
        # Boost confidence if multiple indicators agree
        if scores[best_regime] > 0.5:
            confidence = min(1.0, confidence * 1.2)
        
        return best_regime, confidence
    
    def _default_signal(self) -> RegimeSignal:
        """Return default signal when classification fails"""
        return RegimeSignal(
            regime_type=RegimeType.MEAN_REVERSION,
            trend_direction=TrendDirection.SIDEWAYS,
            volatility_level=VolatilityLevel.MEDIUM,
            bias=Bias.NEUTRAL,
            confidence=0.0
        )

