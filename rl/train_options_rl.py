"""
RL Training Script for Options Trading
Trains PPO/GRPO agents with Greeks, IV metrics, and convexity-aware rewards
"""
import logging
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rl.options_trading_environment import OptionsTradingEnvironment
from rl.options_data_loader import OptionsDataLoader
from rl.ppo_agent import PPOAgent
from rl.grpo_agent import GRPOAgent
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from alpaca_client import AlpacaClient
from config import Config
from alpaca_trade_api.rest import TimeFrame
from core.features.indicators import FeatureEngine
from core.regime.classifier import RegimeClassifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def prepare_options_training_data(
    symbol: str,
    days: int = 365,
    target_dte: int = 7
) -> pd.DataFrame:
    """
    Prepare training data with stock + options features
    
    Args:
        symbol: Trading symbol
        days: Number of days of historical data
        target_dte: Target days to expiration for option selection
        
    Returns:
        DataFrame with OHLCV + options features
    """
    logger.info(f"Preparing options training data for {symbol}...")
    
    # Get historical stock data
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    bars = client.get_historical_bars(symbol, TimeFrame.Day, start_date, end_date)
    
    if bars.empty:
        logger.warning(f"No stock data for {symbol}")
        return pd.DataFrame()
    
    # Calculate technical features
    feature_engine = FeatureEngine()
    regime_classifier = RegimeClassifier()
    
    # Add technical indicators
    features_list = []
    for i in range(len(bars)):
        if i < 50:  # Need enough history
            continue
        
        window = bars.iloc[:i+1]
        features = feature_engine.calculate_all_features(window)
        
        if features:
            regime = regime_classifier.classify(features)
            
            # Add features to dataframe
            row = bars.iloc[i].copy()
            row['rsi'] = features.get('rsi', 50)
            row['ema_9'] = features.get('ema_9', row['close'])
            row['ema_21'] = features.get('ema_21', row['close'])
            row['sma_20'] = features.get('sma_20', row['close'])
            row['atr_pct'] = features.get('atr_pct', 2.0)
            row['adx'] = features.get('adx', 20)
            row['vwap'] = features.get('vwap', row['close'])
            row['vwap_deviation'] = features.get('vwap_deviation', 0)
            row['hurst'] = features.get('hurst', 0.5)
            row['slope'] = features.get('slope', 0)
            row['r_squared'] = features.get('r_squared', 0.5)
            row['regime_type'] = regime.regime_type.value
            
            features_list.append(row)
    
    if not features_list:
        logger.warning(f"No features calculated for {symbol}")
        return pd.DataFrame()
    
    stock_data = pd.DataFrame(features_list)
    
    # Merge with options data
    logger.info(f"Merging options data for {symbol}...")
    data_loader = OptionsDataLoader()
    merged_data = data_loader.load_training_data(
        symbol,
        stock_data,
        target_dte=target_dte,
        use_atm=True
    )
    
    logger.info(f"Prepared {len(merged_data)} rows with options features")
    
    return merged_data

def train_options_agent(
    symbol: str,
    agent_type: str = 'ppo',
    episodes: int = 1000,
    days: int = 365,
    target_dte: int = 7
):
    """
    Train RL agent for options trading
    
    Args:
        symbol: Trading symbol
        agent_type: 'ppo' or 'grpo'
        episodes: Number of training episodes
        days: Days of historical data
        target_dte: Target days to expiration
    """
    logger.info(f"Training {agent_type.upper()} agent for {symbol} options trading")
    
    # Prepare training data
    data = prepare_options_training_data(symbol, days=days, target_dte=target_dte)
    
    if data.empty:
        logger.error(f"No training data available for {symbol}")
        return
    
    logger.info(f"Training data: {len(data)} rows, {len(data.columns)} features")
    logger.info(f"Features: {list(data.columns)}")
    
    # Create environment
    base_env = OptionsTradingEnvironment(
        data=data,
        initial_balance=10000.0,
        commission=1.0,
        max_position_size=0.1,
        lookback_window=50,
        target_dte=target_dte
    )
    
    logger.info(f"Environment created: state_dim={base_env.state_dim}, action_space={base_env.action_space}")
    
    # Wrap environment for stable-baselines3
    monitored_env = Monitor(base_env)
    env = DummyVecEnv([lambda: monitored_env])
    
    # Create agent (using stable-baselines3 interface)
    if agent_type.lower() == 'ppo':
        agent = PPOAgent(
            env=base_env,  # Pass base env, agent will wrap it
            model_path=None,
            learning_rate=3e-4,
            gamma=0.99
        )
        checkpoint_path = f"./models/ppo_options_{symbol}_checkpoints"
    else:
        agent = GRPOAgent(
            env=base_env,  # Pass base env, agent will wrap it
            model_path=None,
            learning_rate=3e-4,
            gamma=0.99
        )
        checkpoint_path = f"./models/grpo_options_{symbol}_checkpoints"
    
    logger.info(f"Agent created: {agent_type.upper()}")
    
    # Calculate timesteps from episodes (estimate ~200 steps per episode)
    timesteps_per_episode = 200
    total_timesteps = episodes * timesteps_per_episode
    
    logger.info(f"Starting training: {episodes} episodes (~{total_timesteps} timesteps)")
    
    # Train using stable-baselines3 interface
    agent.train(
        total_timesteps=total_timesteps,
        checkpoint_freq=timesteps_per_episode * 100,  # Every 100 episodes
        checkpoint_path=checkpoint_path
    )
    
    logger.info("Training complete!")
    
    # Save final model
    final_model_path = f"models/{agent_type}_options_{symbol}_final.zip"
    agent.save(final_model_path)
    logger.info(f"Saved final model: {final_model_path}")

def main():
    parser = argparse.ArgumentParser(description='Train RL agent for options trading')
    parser.add_argument('--symbol', type=str, default='AAPL', help='Trading symbol')
    parser.add_argument('--agent', type=str, default='ppo', choices=['ppo', 'grpo'], help='Agent type')
    parser.add_argument('--episodes', type=int, default=1000, help='Number of episodes')
    parser.add_argument('--days', type=int, default=365, help='Days of historical data')
    parser.add_argument('--dte', type=int, default=7, help='Target days to expiration')
    
    args = parser.parse_args()
    
    train_options_agent(
        symbol=args.symbol,
        agent_type=args.agent,
        episodes=args.episodes,
        days=args.days,
        target_dte=args.dte
    )

if __name__ == '__main__':
    main()

