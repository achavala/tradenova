"""
Feature Engineering Module
Calculates technical indicators, statistical features, and pattern detection
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from scipy import stats
from statsmodels.tsa.stattools import adfuller
import logging

logger = logging.getLogger(__name__)

class FeatureEngine:
    """Feature engineering engine for trading signals"""
    
    def __init__(self):
        """Initialize feature engine"""
        pass
    
    def calculate_all_features(self, df: pd.DataFrame) -> Dict:
        """
        Calculate all features for a symbol
        
        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
            
        Returns:
            Dict with all calculated features
        """
        if df.empty or len(df) < 50:
            logger.warning("Insufficient data for feature calculation")
            return {}
        
        features = {}
        
        # Technical Indicators
        features.update(self._calculate_technical_indicators(df))
        
        # Statistical Features
        features.update(self._calculate_statistical_features(df))
        
        # Pattern Detection
        features.update(self._detect_patterns(df))
        
        return features
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate technical indicators"""
        features = {}
        
        # Ensure we have pandas Series
        close = pd.Series(df['close'].values) if not isinstance(df['close'], pd.Series) else df['close']
        high = pd.Series(df['high'].values) if not isinstance(df['high'], pd.Series) else df['high']
        low = pd.Series(df['low'].values) if not isinstance(df['low'], pd.Series) else df['low']
        volume = pd.Series(df['volume'].values) if not isinstance(df['volume'], pd.Series) else df['volume']
        
        # EMA
        features['ema_9'] = float(close.ewm(span=9, adjust=False).mean().iloc[-1])
        features['ema_21'] = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
        
        # SMA
        features['sma_20'] = float(close.rolling(window=20).mean().iloc[-1])
        
        # RSI
        features['rsi'] = self._calculate_rsi(close, period=14)
        
        # ATR
        features['atr'] = self._calculate_atr(df, period=14)
        features['atr_pct'] = (features['atr'] / close.iloc[-1]) * 100
        
        # ADX
        features['adx'] = self._calculate_adx(df, period=14)
        
        # VWAP (session-based)
        features['vwap'] = self._calculate_vwap(df)
        features['vwap_deviation'] = ((close.iloc[-1] - features['vwap']) / features['vwap']) * 100
        
        return features
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        atr = true_range.rolling(period).mean().iloc[-1]
        return atr if not pd.isna(atr) else df['close'].iloc[-1] * 0.02
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average Directional Index"""
        if len(df) < period + 1:
            return 0.0
        
        try:
            # Ensure we have pandas Series
            high = pd.Series(df['high'].values) if not isinstance(df['high'], pd.Series) else df['high']
            low = pd.Series(df['low'].values) if not isinstance(df['low'], pd.Series) else df['low']
            close = pd.Series(df['close'].values) if not isinstance(df['close'], pd.Series) else df['close']
            
            # Calculate +DM and -DM
            plus_dm = high.diff()
            minus_dm = -low.diff()
            
            plus_dm = plus_dm.where(plus_dm > 0, 0)
            minus_dm = minus_dm.where(minus_dm > 0, 0)
            
            # Calculate True Range for each period
            high_low = high - low
            high_close = np.abs(high - close.shift())
            low_close = np.abs(low - close.shift())
            
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            
            # Calculate smoothed +DM and -DM
            plus_dm_smooth = plus_dm.rolling(period).mean()
            minus_dm_smooth = minus_dm.rolling(period).mean()
            tr_smooth = tr.rolling(period).mean()
            
            # Avoid division by zero
            tr_smooth = tr_smooth.replace(0, np.nan)
            
            plus_di = 100 * (plus_dm_smooth / tr_smooth)
            minus_di = 100 * (minus_dm_smooth / tr_smooth)
            
            # Calculate DX
            di_sum = plus_di + minus_di
            di_sum = di_sum.replace(0, np.nan)  # Avoid division by zero
            
            dx = 100 * np.abs(plus_di - minus_di) / di_sum
            
            # Calculate ADX
            adx = dx.rolling(period).mean().iloc[-1]
            return float(adx) if not pd.isna(adx) else 0.0
        except Exception as e:
            logger.debug(f"Error calculating ADX: {e}")
            return 0.0
    
    def _calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate Volume Weighted Average Price"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).sum() / df['volume'].sum()
        return vwap if not pd.isna(vwap) else df['close'].iloc[-1]
    
    def _calculate_statistical_features(self, df: pd.DataFrame) -> Dict:
        """Calculate statistical features"""
        features = {}
        
        close = df['close']
        
        # Hurst Exponent
        features['hurst'] = self._calculate_hurst(close)
        
        # Linear Regression
        slope, r_squared = self._calculate_linear_regression(close)
        features['slope'] = slope
        features['r_squared'] = r_squared
        
        # Volatility
        returns = close.pct_change().dropna()
        features['volatility'] = returns.std() * np.sqrt(252)  # Annualized
        
        return features
    
    def _calculate_hurst(self, prices: pd.Series, max_lag: int = 20) -> float:
        """
        Calculate Hurst Exponent
        H < 0.5: Mean-reverting
        H = 0.5: Random walk
        H > 0.5: Trending
        """
        if len(prices) < max_lag * 2:
            return 0.5  # Default to random walk
        
        try:
            lags = list(range(2, min(max_lag, len(prices) // 2)))
            if len(lags) < 2:
                return 0.5
            
            tau = []
            for lag in lags:
                if lag >= len(prices):
                    continue
                diff = np.subtract(prices[lag:].values, prices[:-lag].values)
                std_val = np.std(diff)
                if std_val > 0:  # Only include non-zero values
                    tau.append(std_val)
            
            if len(tau) < 2:
                return 0.5
            
            # Filter out zeros and ensure positive values for log
            lags_filtered = []
            tau_filtered = []
            for i, (lag, tau_val) in enumerate(zip(lags[:len(tau)], tau)):
                if tau_val > 0 and lag > 0:
                    lags_filtered.append(lag)
                    tau_filtered.append(tau_val)
            
            if len(lags_filtered) < 2:
                return 0.5
            
            # Fit log-log plot (only if we have valid values)
            lags_array = np.array(lags_filtered)
            tau_array = np.array(tau_filtered)
            
            # Ensure all values are positive for log
            if np.any(lags_array <= 0) or np.any(tau_array <= 0):
                return 0.5
            
            poly = np.polyfit(np.log(lags_array), np.log(tau_array), 1)
            hurst = poly[0]
            
            # Clamp to reasonable range
            return max(0.0, min(1.0, hurst))
        except (ValueError, RuntimeWarning, ZeroDivisionError):
            # Return default if calculation fails
            return 0.5
    
    def _calculate_linear_regression(self, prices: pd.Series) -> tuple:
        """Calculate linear regression slope and R-squared"""
        if len(prices) < 20:
            return 0.0, 0.0
        
        x = np.arange(len(prices))
        y = prices.values
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2
        
        return slope, r_squared
    
    def _detect_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect trading patterns"""
        features = {}
        
        # Fair Value Gap (FVG) detection
        fvg = self._detect_fvg(df)
        features['fvg'] = fvg
        
        return features
    
    def _detect_fvg(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect Fair Value Gap (FVG)
        FVG occurs when there's a gap in price action that tends to fill
        """
        if len(df) < 3:
            return None
        
        # Look for gaps in recent bars
        recent = df.tail(10)
        
        for i in range(1, len(recent) - 1):
            prev_high = recent.iloc[i-1]['high']
            prev_low = recent.iloc[i-1]['low']
            curr_high = recent.iloc[i]['high']
            curr_low = recent.iloc[i]['low']
            next_high = recent.iloc[i+1]['high']
            next_low = recent.iloc[i+1]['low']
            
            # Bullish FVG: gap up that hasn't been filled
            if curr_low > prev_high and next_low > prev_high:
                midpoint = (prev_high + curr_low) / 2
                current_price = df['close'].iloc[-1]
                
                return {
                    'type': 'bullish',
                    'midpoint': midpoint,
                    'top': curr_low,
                    'bottom': prev_high,
                    'distance_pct': ((current_price - midpoint) / midpoint) * 100,
                    'filled': current_price <= prev_high
                }
            
            # Bearish FVG: gap down that hasn't been filled
            if curr_high < prev_low and next_high < prev_low:
                midpoint = (prev_low + curr_high) / 2
                current_price = df['close'].iloc[-1]
                
                return {
                    'type': 'bearish',
                    'midpoint': midpoint,
                    'top': prev_low,
                    'bottom': curr_high,
                    'distance_pct': ((midpoint - current_price) / midpoint) * 100,
                    'filled': current_price >= prev_low
                }
        
        return None

