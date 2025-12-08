"""
Trading Environment for Reinforcement Learning
OpenAI Gym-compatible environment for options trading
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)

class TradingEnvironment(gym.Env):
    """
    Trading environment for RL training
    
    State Space:
    - Technical indicators (RSI, EMA, ATR, ADX, etc.)
    - Regime features (regime type, confidence, volatility)
    - Market features (price, volume, VWAP deviation)
    - IV metrics (IV Rank, IV Percentile)
    - GEX data
    - Position state (current position, P&L)
    
    Action Space:
    - Continuous value [-1, 1]
    - < -0.3: BUY PUT
    - > 0.3: BUY CALL
    - Between: FLAT (no action)
    - Magnitude = confidence/position size
    
    Reward:
    - Correct direction: +reward
    - Wrong direction: -penalty
    - Early exit on profit: +bonus
    - Whipsaw penalty: -penalty
    - Time decay (for options): -small penalty
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(
        self,
        data: pd.DataFrame,
        initial_balance: float = 10000.0,
        commission: float = 1.0,
        max_position_size: float = 0.1,  # 10% of balance
        lookback_window: int = 50
    ):
        """
        Initialize trading environment
        
        Args:
            data: DataFrame with OHLCV and features
            initial_balance: Starting capital
            commission: Commission per trade
            max_position_size: Maximum position size as fraction of balance
            lookback_window: Number of bars to look back
        """
        super().__init__()
        
        self.data = data.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.commission = commission
        self.max_position_size = max_position_size
        self.lookback_window = lookback_window
        
        # State space dimensions
        # Features: price features (5) + technical indicators (10) + regime (4) + IV (2) + position (2) = 23
        self.state_dim = 23
        
        # Action space: continuous [-1, 1]
        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(1,),
            dtype=np.float32
        )
        
        # Observation space
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.state_dim,),
            dtype=np.float32
        )
        
        # Environment state
        self.current_step = 0
        self.balance = initial_balance
        self.position = 0  # -1 = PUT, 0 = FLAT, 1 = CALL
        self.position_entry_price = 0.0
        self.position_entry_step = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        # Track for reward shaping
        self.last_action = 0.0
        self.action_history = []
        self.pnl_history = []
        
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Reset environment to initial state"""
        super().reset(seed=seed)
        
        # Start at random point (but leave room for lookback)
        self.current_step = np.random.randint(
            self.lookback_window,
            len(self.data) - 100  # Leave room for episode
        )
        
        self.balance = self.initial_balance
        self.position = 0
        self.position_entry_price = 0.0
        self.position_entry_step = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.last_action = 0.0
        self.action_history = []
        self.pnl_history = []
        
        observation = self._get_observation()
        info = self._get_info()
        
        return observation, info
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one step in the environment
        
        Args:
            action: Action value [-1, 1]
            
        Returns:
            observation: Next state
            reward: Reward for this step
            terminated: Episode terminated
            truncated: Episode truncated
            info: Additional information
        """
        action_value = float(action[0])
        self.last_action = action_value
        
        # Get current market state
        current_price = self.data.iloc[self.current_step]['close']
        current_features = self._get_current_features()
        
        # Execute action
        reward = 0.0
        trade_executed = False
        
        # Determine action type
        if action_value < -0.3 and self.position != -1:  # BUY PUT
            reward += self._execute_trade(-1, current_price)
            trade_executed = True
        elif action_value > 0.3 and self.position != 1:  # BUY CALL
            reward += self._execute_trade(1, current_price)
            trade_executed = True
        elif abs(action_value) <= 0.3 and self.position != 0:  # FLAT
            reward += self._close_position(current_price)
            trade_executed = True
        
        # Calculate position P&L
        if self.position != 0:
            pnl = self._calculate_pnl(current_price)
            reward += pnl * 0.01  # Small reward for unrealized gains
            self.pnl_history.append(pnl)
        else:
            self.pnl_history.append(0.0)
        
        # Reward shaping
        reward += self._reward_shaping(action_value, current_price)
        
        # Update step
        self.current_step += 1
        self.action_history.append(action_value)
        
        # Check termination
        terminated = False
        truncated = False
        
        if self.current_step >= len(self.data) - 1:
            truncated = True
            # Close any open position
            if self.position != 0:
                final_price = self.data.iloc[-1]['close']
                reward += self._close_position(final_price)
        
        # Check if balance too low
        if self.balance < self.initial_balance * 0.5:  # Lost 50%
            terminated = True
        
        observation = self._get_observation()
        info = self._get_info()
        info['pnl'] = self.total_pnl
        info['trades'] = self.total_trades
        info['win_rate'] = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
        
        return observation, reward, terminated, truncated, info
    
    def _execute_trade(self, direction: int, price: float) -> float:
        """Execute a trade"""
        reward = 0.0
        
        # Close existing position if any
        if self.position != 0:
            reward += self._close_position(price)
        
        # Calculate position size
        position_value = self.balance * self.max_position_size
        position_size = position_value / price
        
        # Execute trade
        cost = position_size * price + self.commission
        
        if cost <= self.balance:
            self.balance -= cost
            self.position = direction
            self.position_entry_price = price
            self.position_entry_step = self.current_step
            self.total_trades += 1
            
            reward -= 0.1  # Small penalty for trading (encourage patience)
        else:
            reward -= 1.0  # Penalty for insufficient funds
        
        return reward
    
    def _close_position(self, price: float) -> float:
        """Close current position"""
        if self.position == 0:
            return 0.0
        
        reward = 0.0
        
        # Calculate P&L
        if self.position == 1:  # CALL
            pnl = (price - self.position_entry_price) / self.position_entry_price
        else:  # PUT
            pnl = (self.position_entry_price - price) / self.position_entry_price
        
        # Calculate return
        position_value = self.balance * self.max_position_size
        pnl_amount = position_value * pnl
        
        self.balance += position_value + pnl_amount - self.commission
        self.total_pnl += pnl_amount
        
        # Reward for correct direction
        if pnl > 0:
            reward += 1.0  # Base reward for profit
            self.winning_trades += 1
            
            # Bonus for early exit on profit
            steps_held = self.current_step - self.position_entry_step
            if steps_held < 5 and pnl > 0.02:  # Exited early with >2% profit
                reward += 0.5
        else:
            reward -= 0.5  # Penalty for loss
        
        # Reset position
        self.position = 0
        self.position_entry_price = 0.0
        self.position_entry_step = 0
        
        return reward
    
    def _calculate_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L"""
        if self.position == 0:
            return 0.0
        
        if self.position == 1:  # CALL
            pnl = (current_price - self.position_entry_price) / self.position_entry_price
        else:  # PUT
            pnl = (self.position_entry_price - current_price) / self.position_entry_price
        
        return pnl
    
    def _reward_shaping(self, action: float, current_price: float) -> float:
        """Additional reward shaping"""
        reward = 0.0
        
        # Penalty for whipsaws (rapid direction changes)
        if len(self.action_history) >= 2:
            last_action = self.action_history[-1]
            if (last_action > 0.3 and action < -0.3) or (last_action < -0.3 and action > 0.3):
                reward -= 0.2  # Whipsaw penalty
        
        # Small penalty for holding too long (time decay simulation)
        if self.position != 0:
            steps_held = self.current_step - self.position_entry_step
            if steps_held > 20:  # Held > 20 steps
                reward -= 0.01 * (steps_held - 20)  # Increasing penalty
        
        return reward
    
    def _get_observation(self) -> np.ndarray:
        """Get current observation/state"""
        if self.current_step < self.lookback_window:
            # Pad with zeros if not enough history
            return np.zeros(self.state_dim, dtype=np.float32)
        
        # Get features from current and recent bars
        features = self._get_current_features()
        
        # Normalize features
        observation = np.array(features, dtype=np.float32)
        
        return observation
    
    def _get_current_features(self) -> List[float]:
        """Extract current features"""
        row = self.data.iloc[self.current_step]
        
        features = []
        
        # Price features (normalized)
        features.append(row.get('close', 0) / 100.0)  # Normalize price
        features.append(row.get('volume', 0) / 1e6)  # Normalize volume
        features.append(row.get('high', 0) / 100.0 - row.get('close', 0) / 100.0)  # High-close
        features.append(row.get('close', 0) / 100.0 - row.get('low', 0) / 100.0)  # Close-low
        features.append((row.get('close', 0) - row.get('open', 0)) / row.get('open', 0) if row.get('open', 0) > 0 else 0)  # Return
        
        # Technical indicators
        features.append(row.get('rsi', 50) / 100.0)  # RSI normalized
        features.append(row.get('ema_9', 0) / 100.0 if 'ema_9' in row else 0)
        features.append(row.get('ema_21', 0) / 100.0 if 'ema_21' in row else 0)
        features.append(row.get('sma_20', 0) / 100.0 if 'sma_20' in row else 0)
        features.append(row.get('atr_pct', 0) / 10.0)  # ATR % normalized
        features.append(row.get('adx', 0) / 100.0)  # ADX normalized
        features.append(row.get('vwap_deviation', 0) / 10.0)  # VWAP deviation
        features.append(row.get('hurst', 0.5))  # Hurst (0-1)
        features.append(row.get('slope', 0) * 1000)  # Slope normalized
        features.append(row.get('r_squared', 0))  # R² (0-1)
        
        # Regime features (one-hot encoded)
        regime_type = row.get('regime_type', 0)
        if isinstance(regime_type, str):
            regime_map = {'TREND': 0, 'MEAN_REVERSION': 1, 'EXPANSION': 2, 'COMPRESSION': 3}
            regime_encoded = [0, 0, 0, 0]
            regime_encoded[regime_map.get(regime_type, 0)] = 1
            features.extend(regime_encoded)
        else:
            features.extend([0, 0, 0, 0])
        
        # IV metrics
        features.append(row.get('iv_rank', 50) / 100.0 if 'iv_rank' in row else 0.5)
        features.append(row.get('iv_percentile', 50) / 100.0 if 'iv_percentile' in row else 0.5)
        
        # Position state
        features.append(float(self.position))  # -1, 0, or 1
        features.append(self._calculate_pnl(row.get('close', 0)) if self.position != 0 else 0.0)  # Current P&L
        
        # Ensure we have exactly state_dim features
        while len(features) < self.state_dim:
            features.append(0.0)
        
        return features[:self.state_dim]
    
    def _get_info(self) -> Dict:
        """Get additional info"""
        return {
            'step': self.current_step,
            'balance': self.balance,
            'position': self.position,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'total_pnl': self.total_pnl
        }
    
    def render(self, mode='human'):
        """Render environment (for visualization)"""
        if mode == 'human':
            print(f"Step: {self.current_step}, Balance: ${self.balance:.2f}, "
                  f"Position: {self.position}, P&L: ${self.total_pnl:.2f}")

