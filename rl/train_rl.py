"""
RL Training Script
Trains PPO/GRPO agents on trading data
"""
import logging
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rl.trading_environment import TradingEnvironment
from rl.ppo_agent import PPOAgent
from rl.grpo_agent import GRPOAgent
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

def prepare_training_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    Prepare training data with features
    
    Args:
        symbol: Trading symbol
        days: Number of days of historical data
        
    Returns:
        DataFrame with OHLCV and features
    """
    logger.info(f"Preparing training data for {symbol}...")
    
    # Get historical data
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    end_date = datetime.now()
    start_date = end_date - pd.Timedelta(days=days)
    
    bars = client.get_historical_bars(symbol, TimeFrame.Day, start_date, end_date)
    
    if bars.empty:
        logger.warning(f"No data for {symbol}, creating sample data")
        # Create sample data for testing
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        prices = 450 + np.cumsum(np.random.randn(len(dates)) * 2)
        bars = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000000, 5000000, len(dates))
        }, index=dates)
    
    # Calculate features
    feature_engine = FeatureEngine()
    regime_classifier = RegimeClassifier()
    
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
            row['iv_rank'] = 50.0  # Placeholder - would come from IV calculator
            row['iv_percentile'] = 50.0
            
            features_list.append(row)
    
    df = pd.DataFrame(features_list)
    logger.info(f"Prepared {len(df)} rows of training data")
    
    return df

def main():
    parser = argparse.ArgumentParser(description='Train RL trading agent')
    parser.add_argument('--agent', type=str, choices=['ppo', 'grpo'], default='ppo',
                       help='Agent type: ppo or grpo')
    parser.add_argument('--symbol', type=str, default='SPY',
                       help='Symbol to train on')
    parser.add_argument('--timesteps', type=int, default=100000,
                       help='Total training timesteps')
    parser.add_argument('--checkpoint-freq', type=int, default=10000,
                       help='Checkpoint frequency')
    parser.add_argument('--model-path', type=str, default=None,
                       help='Path to load existing model')
    parser.add_argument('--days', type=int, default=365,
                       help='Days of historical data')
    
    args = parser.parse_args()
    
    # Prepare data
    data = prepare_training_data(args.symbol, args.days)
    
    if data.empty:
        logger.error("No training data available")
        return
    
    # Create environment
    env = TradingEnvironment(
        data=data,
        initial_balance=10000.0,
        commission=1.0,
        max_position_size=0.1
    )
    
    # Create agent
    if args.agent == 'ppo':
        agent = PPOAgent(env, model_path=args.model_path)
        checkpoint_path = "./models/ppo_checkpoints"
    else:
        agent = GRPOAgent(env, model_path=args.model_path)
        checkpoint_path = "./models/grpo_checkpoints"
    
    # Train
    logger.info(f"Starting {args.agent.upper()} training...")
    agent.train(
        total_timesteps=args.timesteps,
        checkpoint_freq=args.checkpoint_freq,
        checkpoint_path=checkpoint_path
    )
    
    # Save final model
    final_model_path = f"./models/{args.agent}_final"
    agent.save(final_model_path)
    
    logger.info(f"Training complete! Model saved to {final_model_path}")

if __name__ == '__main__':
    main()

