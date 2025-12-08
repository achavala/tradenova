"""
Trading Strategy for TradeNova
Implements swing and scalp strategies for options trading
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from alpaca_trade_api.rest import TimeFrame

logger = logging.getLogger(__name__)

class TradingStrategy:
    """Base trading strategy class"""
    
    def __init__(self, alpaca_client):
        """Initialize strategy with Alpaca client"""
        self.client = alpaca_client
    
    def get_signal(self, symbol: str) -> Optional[Dict]:
        """
        Get trading signal for a symbol
        
        Returns:
            Dict with 'action' ('buy', 'sell', 'hold'), 'confidence', and other metadata
            or None if no signal
        """
        raise NotImplementedError
    
    def should_exit(self, symbol: str, position: Dict) -> bool:
        """Check if position should be exited"""
        raise NotImplementedError

class SwingScalpStrategy(TradingStrategy):
    """
    Combined Swing and Scalp Strategy
    
    Uses multiple indicators:
    - RSI for momentum
    - Moving averages for trend
    - Volume analysis
    - Volatility for options selection
    """
    
    def __init__(self, alpaca_client, lookback_days: int = 20):
        """Initialize strategy"""
        super().__init__(alpaca_client)
        self.lookback_days = lookback_days
    
    def get_signal(self, symbol: str) -> Optional[Dict]:
        """
        Generate trading signal
        
        Returns:
            Dict with signal information or None
        """
        try:
            # Get historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 10)
            
            bars = self.client.get_historical_bars(
                symbol,
                TimeFrame.Day,
                start_date,
                end_date
            )
            
            if bars.empty or len(bars) < 20:
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Calculate indicators
            signals = self._calculate_indicators(bars)
            
            # Generate signal
            signal = self._generate_signal(symbol, signals, bars)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate technical indicators"""
        signals = {}
        
        # RSI
        signals['rsi'] = self._calculate_rsi(df['close'], period=14)
        
        # Moving averages
        signals['sma_20'] = df['close'].rolling(window=20).mean().iloc[-1]
        signals['sma_50'] = df['close'].rolling(window=50).mean().iloc[-1] if len(df) >= 50 else signals['sma_20']
        signals['ema_12'] = df['close'].ewm(span=12, adjust=False).mean().iloc[-1]
        signals['ema_26'] = df['close'].ewm(span=26, adjust=False).mean().iloc[-1] if len(df) >= 26 else signals['ema_12']
        
        # Volume
        signals['volume_sma'] = df['volume'].rolling(window=20).mean().iloc[-1]
        signals['current_volume'] = df['volume'].iloc[-1]
        signals['volume_ratio'] = signals['current_volume'] / signals['volume_sma'] if signals['volume_sma'] > 0 else 1
        
        # Volatility (ATR)
        signals['atr'] = self._calculate_atr(df, period=14)
        signals['volatility_pct'] = (signals['atr'] / df['close'].iloc[-1]) * 100
        
        # Price action
        signals['current_price'] = df['close'].iloc[-1]
        signals['high_20'] = df['high'].rolling(window=20).max().iloc[-1]
        signals['low_20'] = df['low'].rolling(window=20).min().iloc[-1]
        signals['price_position'] = (signals['current_price'] - signals['low_20']) / (signals['high_20'] - signals['low_20']) if (signals['high_20'] - signals['low_20']) > 0 else 0.5
        
        # Momentum
        signals['momentum'] = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5] if len(df) >= 5 else 0
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        atr = true_range.rolling(period).mean().iloc[-1]
        return atr if not pd.isna(atr) else df['close'].iloc[-1] * 0.02
    
    def _generate_signal(self, symbol: str, signals: Dict, df: pd.DataFrame) -> Optional[Dict]:
        """Generate buy/sell signal based on indicators"""
        
        score = 0
        reasons = []
        
        # RSI signals
        if signals['rsi'] < 30:
            score += 2
            reasons.append("Oversold (RSI < 30)")
        elif signals['rsi'] < 40:
            score += 1
            reasons.append("Near oversold (RSI < 40)")
        elif signals['rsi'] > 70:
            score -= 2
            reasons.append("Overbought (RSI > 70)")
        elif signals['rsi'] > 60:
            score -= 1
            reasons.append("Near overbought (RSI > 60)")
        
        # Moving average signals
        if signals['ema_12'] > signals['ema_26']:
            score += 1
            reasons.append("Bullish EMA crossover")
        else:
            score -= 1
            reasons.append("Bearish EMA crossover")
        
        if signals['current_price'] > signals['sma_20']:
            score += 1
            reasons.append("Price above SMA20")
        else:
            score -= 1
            reasons.append("Price below SMA20")
        
        # Volume confirmation
        if signals['volume_ratio'] > 1.5:
            score += 1
            reasons.append(f"High volume ({signals['volume_ratio']:.2f}x)")
        elif signals['volume_ratio'] < 0.5:
            score -= 1
            reasons.append(f"Low volume ({signals['volume_ratio']:.2f}x)")
        
        # Momentum
        if signals['momentum'] > 0.02:
            score += 1
            reasons.append("Positive momentum")
        elif signals['momentum'] < -0.02:
            score -= 1
            reasons.append("Negative momentum")
        
        # Price position
        if signals['price_position'] < 0.3:
            score += 1
            reasons.append("Near support")
        elif signals['price_position'] > 0.7:
            score -= 1
            reasons.append("Near resistance")
        
        # Volatility filter (for options, we want some volatility)
        if signals['volatility_pct'] < 1:
            score -= 1
            reasons.append("Low volatility")
        
        # Generate signal
        if score >= 3:
            confidence = min(score / 5.0, 1.0)
            return {
                'action': 'buy',
                'symbol': symbol,
                'confidence': confidence,
                'score': score,
                'reasons': reasons,
                'current_price': signals['current_price'],
                'indicators': {
                    'rsi': signals['rsi'],
                    'volatility_pct': signals['volatility_pct'],
                    'volume_ratio': signals['volume_ratio']
                }
            }
        elif score <= -3:
            return {
                'action': 'sell',
                'symbol': symbol,
                'confidence': min(abs(score) / 5.0, 1.0),
                'score': score,
                'reasons': reasons
            }
        
        return {
            'action': 'hold',
            'symbol': symbol,
            'confidence': 0.5,
            'score': score,
            'reasons': reasons
        }
    
    def should_exit(self, symbol: str, position: Dict) -> bool:
        """Check if position should be exited based on strategy"""
        # This is handled by Position class with profit targets and stop loss
        # Strategy can add additional exit logic here if needed
        return False

