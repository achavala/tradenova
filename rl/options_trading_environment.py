"""
Enhanced Options Trading Environment for RL
Includes Greeks, IV metrics, volatility regime, and convexity-aware rewards
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class OptionsTradingEnvironment(gym.Env):
    """
    Enhanced trading environment for options RL training
    
    State Space (40+ features):
    - Price features (5)
    - Technical indicators (10)
    - Regime features (4)
    - Greeks (4): Delta, Gamma, Theta, Vega
    - IV metrics (4): IV, IV Rank, IV Percentile, IV std
    - Option features (4): Strike, DTE, OI, spread
    - Microstructure (2): Bid/ask spread, volume
    - Position state (2)
    - Volatility regime (2): Regime confidence, volatility level
    
    Action Space:
    - Continuous value [-1, 1]
    - < -0.3: BUY PUT
    - > 0.3: BUY CALL
    - Between: FLAT (no action)
    
    Reward (Convexity-Aware):
    - Convexity PnL (gamma efficiency)
    - UVaR penalty
    - Theta burn penalty
    - Slippage penalty
    - IV crush penalty
    """
    
    metadata = {'render_modes': ['human']}
    
    def __init__(
        self,
        data: pd.DataFrame,
        initial_balance: float = 10000.0,
        commission: float = 1.0,
        max_position_size: float = 0.1,  # 10% of balance
        lookback_window: int = 50,
        target_dte: int = 7,  # Target days to expiration
        risk_free_rate: float = 0.05
    ):
        """
        Initialize options trading environment
        
        Args:
            data: DataFrame with OHLCV + options features (from OptionsDataLoader)
            initial_balance: Starting capital
            commission: Commission per trade
            max_position_size: Maximum position size as fraction of balance
            lookback_window: Number of bars to look back
            target_dte: Target days to expiration
            risk_free_rate: Risk-free rate for calculations
        """
        super().__init__()
        
        self.data = data.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.commission = commission
        self.max_position_size = max_position_size
        self.lookback_window = lookback_window
        self.target_dte = target_dte
        self.risk_free_rate = risk_free_rate
        
        # Enhanced state space dimensions
        # Price (5) + Technicals (10) + Regime (4) + Greeks (4) + IV (4) + 
        # Option (4) + Microstructure (2) + Position (2) + Vol Regime (2) = 37
        self.state_dim = 37
        
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
        self.position_entry_greeks = {}  # Store Greeks at entry
        self.position_entry_step = 0
        self.position_entry_dte = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        # Track for reward shaping
        self.last_action = 0.0
        self.action_history = []
        self.pnl_history = []
        self.theta_burn_total = 0.0  # Track total theta burn
        
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """Reset environment to initial state"""
        super().reset(seed=seed)
        
        # Check if we have enough data
        if len(self.data) < self.lookback_window + 10:
            # Not enough data, return zero observation
            self.current_step = 0
            observation = np.zeros(self.state_dim, dtype=np.float32)
            info = self._get_info()
            return observation, info
        
        # Start at random point (but leave room for lookback)
        min_step = self.lookback_window
        max_step = max(min_step + 1, len(self.data) - 100)  # Leave room for episode
        
        if max_step <= min_step:
            # Not enough data, start at lookback window
            self.current_step = min(min_step, len(self.data) - 1)
        else:
            self.current_step = np.random.randint(min_step, max_step)
        
        self.balance = self.initial_balance
        self.position = 0
        self.position_entry_price = 0.0
        self.position_entry_greeks = {}
        self.position_entry_step = 0
        self.position_entry_dte = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.last_action = 0.0
        self.action_history = []
        self.pnl_history = []
        self.theta_burn_total = 0.0
        
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
            reward: Convexity-aware reward
            terminated: Episode terminated
            truncated: Episode truncated
            info: Additional information
        """
        action_value = float(action[0])
        self.last_action = action_value
        
        # Get current market state
        row = self.data.iloc[self.current_step]
        current_price = row.get('close', 0)
        current_greeks = self._get_current_greeks(row)
        
        # Execute action
        reward = 0.0
        trade_executed = False
        
        # Determine action type
        if action_value < -0.3 and self.position != -1:  # BUY PUT
            reward += self._execute_trade(-1, current_price, current_greeks, row)
            trade_executed = True
        elif action_value > 0.3 and self.position != 1:  # BUY CALL
            reward += self._execute_trade(1, current_price, current_greeks, row)
            trade_executed = True
        elif abs(action_value) <= 0.3 and self.position != 0:  # FLAT
            reward += self._close_position(current_price, row)
            trade_executed = True
        
        # Calculate convexity-aware P&L and reward
        if self.position != 0:
            convexity_pnl, theta_burn = self._calculate_convexity_pnl(row, current_price)
            reward += convexity_pnl
            self.theta_burn_total += theta_burn
            self.pnl_history.append(convexity_pnl)
        else:
            self.pnl_history.append(0.0)
        
        # Convexity-aware reward shaping
        reward += self._convexity_reward_shaping(action_value, row, current_price)
        
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
                reward += self._close_position(final_price, self.data.iloc[-1])
        
        # Check if balance too low
        if self.balance < self.initial_balance * 0.5:  # Lost 50%
            terminated = True
        
        observation = self._get_observation()
        info = self._get_info()
        info['pnl'] = self.total_pnl
        info['trades'] = self.total_trades
        info['win_rate'] = self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
        info['theta_burn'] = self.theta_burn_total
        
        return observation, reward, terminated, truncated, info
    
    def _execute_trade(
        self,
        direction: int,
        price: float,
        greeks: Dict,
        row: pd.Series
    ) -> float:
        """Execute a trade with Greeks tracking"""
        reward = 0.0
        
        # Close existing position if any
        if self.position != 0:
            reward += self._close_position(price, row)
        
        # Get option price (use last or mid)
        option_price = row.get('option_price', 0) or price * 0.1  # Fallback
        
        # Calculate position size
        position_value = self.balance * self.max_position_size
        position_size = position_value / option_price if option_price > 0 else 0
        
        # Execute trade
        cost = position_size * option_price + self.commission
        
        if cost <= self.balance and option_price > 0:
            self.balance -= cost
            self.position = direction
            self.position_entry_price = option_price
            self.position_entry_greeks = greeks.copy()
            self.position_entry_step = self.current_step
            self.position_entry_dte = row.get('dte', self.target_dte)
            self.total_trades += 1
            
            # Small penalty for trading (encourage patience)
            reward -= 0.1
        else:
            reward -= 1.0  # Penalty for insufficient funds
        
        return reward
    
    def _close_position(self, price: float, row: pd.Series) -> float:
        """Close current position with convexity-aware P&L"""
        if self.position == 0:
            return 0.0
        
        reward = 0.0
        
        # Get current option price
        current_option_price = row.get('option_price', 0) or self.position_entry_price
        
        # Calculate P&L
        if self.position == 1:  # CALL
            pnl_pct = (current_option_price - self.position_entry_price) / self.position_entry_price if self.position_entry_price > 0 else 0
        else:  # PUT
            pnl_pct = (self.position_entry_price - current_option_price) / self.position_entry_price if self.position_entry_price > 0 else 0
        
        # Calculate return
        position_value = self.balance * self.max_position_size
        pnl_amount = position_value * pnl_pct
        
        # Convexity bonus/penalty
        convexity_bonus = self._calculate_convexity_bonus(row, pnl_pct)
        reward += convexity_bonus
        
        self.balance += position_value + pnl_amount - self.commission
        self.total_pnl += pnl_amount
        
        # Reward for correct direction
        if pnl_pct > 0:
            reward += 1.0  # Base reward for profit
            self.winning_trades += 1
            
            # Bonus for gamma efficiency (quick moves)
            steps_held = self.current_step - self.position_entry_step
            if steps_held < 5 and pnl_pct > 0.02:  # Exited early with >2% profit
                reward += 0.5
        else:
            reward -= 0.5  # Penalty for loss
        
        # Reset position
        self.position = 0
        self.position_entry_price = 0.0
        self.position_entry_greeks = {}
        self.position_entry_step = 0
        self.position_entry_dte = 0
        
        return reward
    
    def _calculate_convexity_pnl(self, row: pd.Series, current_price: float) -> Tuple[float, float]:
        """
        Calculate convexity-aware P&L
        
        Returns:
            (convexity_pnl, theta_burn)
        """
        if self.position == 0:
            return 0.0, 0.0
        
        # Get current Greeks
        current_greeks = self._get_current_greeks(row)
        entry_greeks = self.position_entry_greeks
        
        # Calculate price move
        price_move = current_price - row.get('underlying_price', current_price)
        price_move_pct = price_move / current_price if current_price > 0 else 0
        
        # Gamma P&L (convexity benefit)
        # Gamma P&L ≈ 0.5 * Gamma * (price_move)^2
        gamma = current_greeks.get('gamma', 0.0)
        gamma_pnl = 0.5 * gamma * (price_move_pct ** 2) * 100  # Scale
        
        # Delta P&L (linear)
        delta = current_greeks.get('delta', 0.5)
        delta_pnl = delta * price_move_pct * 100  # Scale
        
        # Theta burn (time decay)
        theta = current_greeks.get('theta', 0.0)
        days_held = self.current_step - self.position_entry_step
        theta_burn = abs(theta) * days_held * 0.1  # Scale
        
        # Total convexity P&L
        convexity_pnl = (delta_pnl + gamma_pnl - theta_burn) * 0.01  # Normalize
        
        return convexity_pnl, theta_burn
    
    def _calculate_convexity_bonus(self, row: pd.Series, pnl_pct: float) -> float:
        """Calculate bonus for gamma efficiency"""
        if self.position == 0:
            return 0.0
        
        # Get gamma at entry
        entry_gamma = self.position_entry_greeks.get('gamma', 0.0)
        
        # Bonus for high gamma efficiency (quick moves with high gamma)
        steps_held = self.current_step - self.position_entry_step
        if steps_held > 0 and entry_gamma > 0:
            gamma_efficiency = abs(pnl_pct) / steps_held  # P&L per step
            if gamma_efficiency > 0.01:  # >1% per step
                return min(0.5, gamma_efficiency * 10)  # Cap at 0.5
        
        return 0.0
    
    def _convexity_reward_shaping(
        self,
        action: float,
        row: pd.Series,
        current_price: float
    ) -> float:
        """
        Convexity-aware reward shaping
        
        Reward = convexity PnL - UVaR - theta burn - slippage - IV crush
        """
        reward = 0.0
        
        # Penalty for whipsaws
        if len(self.action_history) >= 2:
            last_action = self.action_history[-1]
            if (last_action > 0.3 and action < -0.3) or (last_action < -0.3 and action > 0.3):
                reward -= 0.2  # Whipsaw penalty
        
        if self.position != 0:
            # Theta burn penalty (increasing with time)
            steps_held = self.current_step - self.position_entry_step
            current_theta = self._get_current_greeks(row).get('theta', 0.0)
            if steps_held > 0:
                theta_penalty = abs(current_theta) * steps_held * 0.001
                reward -= theta_penalty
            
            # IV crush penalty (if IV decreased significantly)
            entry_iv = self.position_entry_greeks.get('iv', 0.2)
            current_iv = row.get('implied_volatility', 0.2)
            if entry_iv > 0 and current_iv < entry_iv * 0.9:  # IV dropped >10%
                iv_crush = (entry_iv - current_iv) / entry_iv
                reward -= iv_crush * 0.5  # Penalty for IV crush
            
            # Slippage penalty (bid/ask spread)
            spread = row.get('bid_ask_spread', 0.05)
            reward -= spread * 0.1  # Small penalty for wide spreads
        
        return reward
    
    def _get_current_greeks(self, row: pd.Series) -> Dict:
        """Get current Greeks from row"""
        return {
            'delta': float(row.get('delta', 0.5)),
            'gamma': float(row.get('gamma', 0.0)),
            'theta': float(row.get('theta', 0.0)),
            'vega': float(row.get('vega', 0.0)),
            'iv': float(row.get('implied_volatility', 0.2))
        }
    
    def _get_observation(self) -> np.ndarray:
        """Get current observation/state with enhanced features"""
        if len(self.data) == 0:
            return np.zeros(self.state_dim, dtype=np.float32)
        
        if self.current_step < self.lookback_window or self.current_step >= len(self.data):
            return np.zeros(self.state_dim, dtype=np.float32)
        
        features = self._get_current_features()
        observation = np.array(features, dtype=np.float32)
        
        return observation
    
    def _get_current_features(self) -> List[float]:
        """Extract current features with Greeks and IV"""
        row = self.data.iloc[self.current_step]
        
        # Helper to safely get scalar values
        def get_scalar(key, default=0.0):
            value = row.get(key, default)
            if hasattr(value, 'iloc'):  # It's a Series
                return float(value.iloc[0]) if len(value) > 0 else default
            elif hasattr(value, 'item'):  # It's a numpy scalar
                return float(value.item())
            else:
                return float(value) if value is not None else default
        
        features = []
        
        # Price features (5)
        close = get_scalar('close', 0)
        volume = get_scalar('volume', 0)
        high = get_scalar('high', 0)
        low = get_scalar('low', 0)
        open_price = get_scalar('open', 0)
        
        features.append(close / 100.0)  # Normalize price
        features.append(volume / 1e6)  # Normalize volume
        features.append(high / 100.0 - close / 100.0)  # High-close
        features.append(close / 100.0 - low / 100.0)  # Close-low
        features.append((close - open_price) / open_price if open_price > 0 else 0)  # Return
        
        # Technical indicators (10)
        features.append(get_scalar('rsi', 50) / 100.0)  # RSI normalized
        features.append(get_scalar('ema_9', 0) / 100.0)
        features.append(get_scalar('ema_21', 0) / 100.0)
        features.append(get_scalar('sma_20', 0) / 100.0)
        features.append(get_scalar('atr_pct', 0) / 10.0)  # ATR % normalized
        features.append(get_scalar('adx', 0) / 100.0)  # ADX normalized
        features.append(get_scalar('vwap_deviation', 0) / 10.0)  # VWAP deviation
        features.append(get_scalar('hurst', 0.5))  # Hurst (0-1)
        features.append(get_scalar('slope', 0) * 1000)  # Slope normalized
        features.append(get_scalar('r_squared', 0))  # R² (0-1)
        
        # Regime features (4) - one-hot encoded
        regime_type = row.get('regime_type', 0)
        # Handle Series case
        if hasattr(regime_type, 'iloc'):
            regime_type = regime_type.iloc[0] if len(regime_type) > 0 else 0
        elif hasattr(regime_type, 'item'):
            regime_type = regime_type.item()
        
        if isinstance(regime_type, str):
            regime_map = {'TREND': 0, 'MEAN_REVERSION': 1, 'EXPANSION': 2, 'COMPRESSION': 3}
            regime_encoded = [0, 0, 0, 0]
            regime_encoded[regime_map.get(regime_type, 0)] = 1
            features.extend(regime_encoded)
        else:
            features.extend([0, 0, 0, 0])
        
        # Greeks (4) - NEW
        features.append(get_scalar('delta', 0.5))  # Delta (0-1)
        features.append(get_scalar('gamma', 0.0) * 1000)  # Gamma (normalized)
        features.append(get_scalar('theta', 0.0) * 100)  # Theta (normalized, usually negative)
        features.append(get_scalar('vega', 0.0) * 100)  # Vega (normalized)
        
        # IV metrics (4) - NEW from collected data
        features.append(get_scalar('implied_volatility', 0.2))  # IV (0-1, typically 0.1-0.5)
        features.append(get_scalar('iv_rank', 50) / 100.0)  # IV Rank (0-1)
        features.append(get_scalar('iv_percentile', 50) / 100.0)  # IV Percentile (0-1)
        features.append(get_scalar('iv_std', 0.05) * 10)  # IV std (normalized)
        
        # Option features (4) - NEW
        strike = get_scalar('strike', 0)
        underlying = close  # Use already extracted close price
        moneyness = (strike / underlying) if underlying > 0 else 1.0  # Moneyness
        features.append(moneyness)  # Strike/underlying ratio
        features.append(get_scalar('dte', self.target_dte) / 30.0)  # DTE normalized (0-1 for 0-30 DTE)
        oi = get_scalar('open_interest', 0)
        features.append(min(oi / 10000.0, 1.0))  # OI normalized
        features.append(get_scalar('bid_ask_spread', 0.05))  # Spread (0-1)
        
        # Microstructure (2) - NEW
        # Use option volume if available, otherwise stock volume
        if 'option_volume' in row.index:
            option_volume = get_scalar('option_volume', 0)
        else:
            option_volume = volume  # Fall back to stock volume
        features.append(get_scalar('bid_ask_spread', 0.05))  # Spread
        features.append(min(option_volume / 1000.0, 1.0))  # Volume normalized
        
        # Position state (2)
        features.append(float(self.position))  # -1, 0, or 1
        current_pnl = self._calculate_pnl(close) if self.position != 0 else 0.0
        features.append(current_pnl)  # Current P&L
        
        # Volatility regime (2) - NEW
        # Regime confidence (from existing regime)
        has_regime = regime_type is not None and (isinstance(regime_type, str) or regime_type != 0)
        regime_confidence = 1.0 if has_regime else 0.5
        features.append(regime_confidence)
        # Volatility level (from ATR or IV)
        atr_pct = get_scalar('atr_pct', 2.0)
        vol_level = min(atr_pct / 10.0, 1.0)  # Normalized volatility
        features.append(vol_level)
        
        # Ensure we have exactly state_dim features
        while len(features) < self.state_dim:
            features.append(0.0)
        
        return features[:self.state_dim]
    
    def _calculate_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L"""
        if self.position == 0:
            return 0.0
        
        # Simplified P&L calculation
        if self.position == 1:  # CALL
            pnl = (current_price - self.position_entry_price) / self.position_entry_price if self.position_entry_price > 0 else 0
        else:  # PUT
            pnl = (self.position_entry_price - current_price) / self.position_entry_price if self.position_entry_price > 0 else 0
        
        return pnl
    
    def _get_info(self) -> Dict:
        """Get additional info"""
        return {
            'step': self.current_step,
            'balance': self.balance,
            'position': self.position,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'total_pnl': self.total_pnl,
            'theta_burn': self.theta_burn_total
        }
    
    def render(self, mode='human'):
        """Render environment (for visualization)"""
        if mode == 'human':
            row = self.data.iloc[self.current_step] if self.current_step < len(self.data) else None
            greeks_str = ""
            if row is not None:
                greeks_str = f"Δ={row.get('delta', 0):.3f} Γ={row.get('gamma', 0):.6f} θ={row.get('theta', 0):.3f} ν={row.get('vega', 0):.3f}"
            
            print(f"Step: {self.current_step}, Balance: ${self.balance:.2f}, "
                  f"Position: {self.position}, P&L: ${self.total_pnl:.2f}, "
                  f"Theta Burn: ${self.theta_burn_total:.2f}")
            if greeks_str:
                print(f"  Greeks: {greeks_str}")

