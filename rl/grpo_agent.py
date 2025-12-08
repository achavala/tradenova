"""
GRPO (Group Relative Policy Optimization) Agent
Improved stability variant of PPO
"""
import logging
from typing import Optional
import numpy as np
import sys
from pathlib import Path
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

from rl.trading_environment import TradingEnvironment

logger = logging.getLogger(__name__)

class GRPOAgent:
    """
    GRPO Agent - Group Relative Policy Optimization
    
    Key differences from PPO:
    - Uses relative rewards (normalized within episode group)
    - More stable learning in non-stationary environments
    - Better handling of reward scaling
    """
    
    def __init__(
        self,
        env: TradingEnvironment,
        model_path: Optional[str] = None,
        learning_rate: float = 3e-4,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_range: float = 0.15,  # Slightly tighter clip for stability
        ent_coef: float = 0.02,  # Higher entropy for exploration
        vf_coef: float = 0.5,
        max_grad_norm: float = 0.5,
        normalize_advantage: bool = True  # GRPO feature
    ):
        """
        Initialize GRPO Agent
        
        Args:
            env: Trading environment
            model_path: Path to load existing model
            learning_rate: Learning rate (lower for stability)
            n_steps: Steps per update
            batch_size: Batch size
            n_epochs: Number of epochs per update
            gamma: Discount factor
            gae_lambda: GAE lambda
            clip_range: PPO clip range (tighter for GRPO)
            ent_coef: Entropy coefficient (higher for exploration)
            vf_coef: Value function coefficient
            max_grad_norm: Max gradient norm
            normalize_advantage: Normalize advantages (GRPO feature)
        """
        self.env = env
        self.normalize_advantage = normalize_advantage
        
        # Wrap environment
        self.monitored_env = Monitor(env)
        self.vec_env = DummyVecEnv([lambda: self.monitored_env])
        
        # Create or load model
        if model_path and os.path.exists(model_path):
            logger.info(f"Loading GRPO model from {model_path}")
            self.model = PPO.load(model_path, env=self.vec_env)
        else:
            logger.info("Creating new GRPO model")
            # Use PPO with GRPO-optimized hyperparameters
            self.model = PPO(
                "MlpPolicy",
                self.vec_env,
                learning_rate=learning_rate * 0.8,  # Slightly lower LR for stability
                n_steps=n_steps,
                batch_size=batch_size,
                n_epochs=n_epochs,
                gamma=gamma,
                gae_lambda=gae_lambda,
                clip_range=clip_range,
                ent_coef=ent_coef,
                vf_coef=vf_coef,
                max_grad_norm=max_grad_norm,
                normalize_advantage=normalize_advantage,
                verbose=1,
                tensorboard_log="./logs/tensorboard/"
            )
    
    def train(
        self,
        total_timesteps: int = 100000,
        checkpoint_freq: int = 10000,
        checkpoint_path: str = "./models/grpo_checkpoints"
    ):
        """
        Train the GRPO agent
        
        Args:
            total_timesteps: Total training timesteps
            checkpoint_freq: Frequency of checkpoints
            checkpoint_path: Path to save checkpoints
        """
        os.makedirs(checkpoint_path, exist_ok=True)
        
        from stable_baselines3.common.callbacks import CheckpointCallback
        from rl.ppo_agent import TradingCallback
        
        callbacks = [
            TradingCallback(),
            CheckpointCallback(
                save_freq=checkpoint_freq,
                save_path=checkpoint_path,
                name_prefix="grpo_trading"
            )
        ]
        
        logger.info(f"Starting GRPO training for {total_timesteps} timesteps")
        
        # Check if progress bar dependencies are available
        try:
            import tqdm
            import rich
            use_progress_bar = True
        except ImportError:
            use_progress_bar = False
            logger.warning("tqdm/rich not available, progress bar disabled")
        
        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks,
            progress_bar=use_progress_bar
        )
        
        logger.info("GRPO training completed")
    
    def predict(
        self,
        observation: np.ndarray,
        deterministic: bool = False,
        apply_smoothing: bool = True
    ) -> tuple:
        """
        Predict action with optional EMA smoothing
        
        Args:
            observation: Current state
            deterministic: Use deterministic policy
            apply_smoothing: Apply EMA smoothing to predictions
            
        Returns:
            action: Predicted action (smoothed if enabled)
            state: Hidden state
        """
        action, state = self.model.predict(observation, deterministic=deterministic)
        
        # Apply EMA smoothing to reduce noise
        if apply_smoothing and not hasattr(self, 'action_ema'):
            self.action_ema = action[0]
        elif apply_smoothing:
            alpha = 0.3  # EMA smoothing factor
            self.action_ema = alpha * action[0] + (1 - alpha) * self.action_ema
            action = np.array([[self.action_ema]])
        
        return action, state
    
    def save(self, path: str):
        """Save model"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.model.save(path)
        logger.info(f"GRPO model saved to {path}")
    
    def load(self, path: str):
        """Load model"""
        self.model = PPO.load(path, env=self.vec_env)
        logger.info(f"GRPO model loaded from {path}")

