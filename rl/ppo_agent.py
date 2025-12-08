"""
PPO (Proximal Policy Optimization) Agent for Trading
Uses stable-baselines3 for PPO implementation
"""
import logging
from typing import Optional, Dict
import numpy as np
import sys
from pathlib import Path
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

from rl.trading_environment import TradingEnvironment

logger = logging.getLogger(__name__)

class TradingCallback(BaseCallback):
    """Callback for tracking training progress"""
    
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
        self.episode_pnls = []
        
    def _on_step(self) -> bool:
        """Called at each step"""
        return True
    
    def _on_rollout_end(self) -> None:
        """Called at end of rollout"""
        if len(self.locals.get('infos', [])) > 0:
            for info in self.locals['infos']:
                if 'episode' in info:
                    self.episode_rewards.append(info['episode']['r'])
                    self.episode_lengths.append(info['episode']['l'])
                if 'pnl' in info:
                    self.episode_pnls.append(info['pnl'])

class PPOAgent:
    """PPO Agent for trading"""
    
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
        clip_range: float = 0.2,
        ent_coef: float = 0.01,
        vf_coef: float = 0.5,
        max_grad_norm: float = 0.5
    ):
        """
        Initialize PPO Agent
        
        Args:
            env: Trading environment
            model_path: Path to load existing model
            learning_rate: Learning rate
            n_steps: Steps per update
            batch_size: Batch size
            n_epochs: Number of epochs per update
            gamma: Discount factor
            gae_lambda: GAE lambda
            clip_range: PPO clip range
            ent_coef: Entropy coefficient
            vf_coef: Value function coefficient
            max_grad_norm: Max gradient norm
        """
        self.env = env
        
        # Wrap environment
        self.monitored_env = Monitor(env)
        self.vec_env = DummyVecEnv([lambda: self.monitored_env])
        
        # Create or load model
        if model_path and os.path.exists(model_path):
            logger.info(f"Loading PPO model from {model_path}")
            self.model = PPO.load(model_path, env=self.vec_env)
        else:
            logger.info("Creating new PPO model")
            self.model = PPO(
                "MlpPolicy",
                self.vec_env,
                learning_rate=learning_rate,
                n_steps=n_steps,
                batch_size=batch_size,
                n_epochs=n_epochs,
                gamma=gamma,
                gae_lambda=gae_lambda,
                clip_range=clip_range,
                ent_coef=ent_coef,
                vf_coef=vf_coef,
                max_grad_norm=max_grad_norm,
                verbose=1,
                tensorboard_log="./logs/tensorboard/"
            )
    
    def train(
        self,
        total_timesteps: int = 100000,
        checkpoint_freq: int = 10000,
        checkpoint_path: str = "./models/ppo_checkpoints"
    ):
        """
        Train the PPO agent
        
        Args:
            total_timesteps: Total training timesteps
            checkpoint_freq: Frequency of checkpoints
            checkpoint_path: Path to save checkpoints
        """
        os.makedirs(checkpoint_path, exist_ok=True)
        
        # Callbacks
        callbacks = [
            TradingCallback(),
            CheckpointCallback(
                save_freq=checkpoint_freq,
                save_path=checkpoint_path,
                name_prefix="ppo_trading"
            )
        ]
        
        logger.info(f"Starting PPO training for {total_timesteps} timesteps")
        
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
        
        logger.info("Training completed")
    
    def predict(
        self,
        observation: np.ndarray,
        deterministic: bool = False
    ) -> tuple:
        """
        Predict action from observation
        
        Args:
            observation: Current state
            deterministic: Use deterministic policy
            
        Returns:
            action: Predicted action
            state: Hidden state (for RNN policies)
        """
        action, state = self.model.predict(observation, deterministic=deterministic)
        return action, state
    
    def save(self, path: str):
        """Save model"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.model.save(path)
        logger.info(f"Model saved to {path}")
    
    def load(self, path: str):
        """Load model"""
        self.model = PPO.load(path, env=self.vec_env)
        logger.info(f"Model loaded from {path}")

