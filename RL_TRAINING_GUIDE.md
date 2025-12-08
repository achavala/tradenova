# RL Training Guide - Quick Start

## ✅ Import Issue Fixed

The import paths have been fixed. You can now run the training script!

## 🚀 Quick Start

### 1. Install RL Dependencies (if not already installed)

```bash
source venv/bin/activate
pip install stable-baselines3 torch tensorboard
```

### 2. Run Training

```bash
# Train GRPO agent on TSLA
python rl/train_rl.py --agent grpo --symbol TSLA --timesteps 100000

# Train PPO agent on SPY
python rl/train_rl.py --agent ppo --symbol SPY --timesteps 100000

# With custom checkpoint frequency
python rl/train_rl.py --agent grpo --symbol TSLA --timesteps 100000 --checkpoint-freq 5000
```

### 3. Monitor Training

Training logs will be saved to:
- `./logs/tensorboard/` - TensorBoard logs (view with `tensorboard --logdir ./logs/tensorboard`)
- `./models/ppo_checkpoints/` or `./models/grpo_checkpoints/` - Model checkpoints

## 📊 Training Options

```bash
python rl/train_rl.py --help
```

**Options:**
- `--agent {ppo,grpo}` - Agent type (default: ppo)
- `--symbol SYMBOL` - Symbol to train on (default: SPY)
- `--timesteps TIMESTEPS` - Total training timesteps (default: 100000)
- `--checkpoint-freq CHECKPOINT_FREQ` - Checkpoint frequency (default: 10000)
- `--model-path MODEL_PATH` - Path to load existing model
- `--days DAYS` - Days of historical data (default: 365)

## 🎯 Example Commands

```bash
# Quick test (10K timesteps)
python rl/train_rl.py --agent grpo --symbol SPY --timesteps 10000

# Full training (100K timesteps)
python rl/train_rl.py --agent grpo --symbol TSLA --timesteps 100000

# Continue training from checkpoint
python rl/train_rl.py --agent grpo --symbol SPY --timesteps 50000 --model-path ./models/grpo_checkpoints/grpo_trading_100000_steps

# Train on different symbol with more data
python rl/train_rl.py --agent ppo --symbol AAPL --timesteps 200000 --days 730
```

## 📝 Notes

- **Gym Warning**: The warning about Gym vs Gymnasium is harmless - the code uses Gymnasium
- **Training Time**: 100K timesteps can take 30-60 minutes depending on your system
- **Data**: If Alpaca API is unavailable, the script will create sample data for testing
- **Checkpoints**: Models are saved every N timesteps (default: 10000)

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'rl'"
✅ **Fixed!** The import paths have been corrected.

### "No module named 'stable_baselines3'"
```bash
pip install stable-baselines3
```

### "No module named 'torch'"
```bash
pip install torch
```

### Out of Memory
- Reduce `--timesteps` or `--days`
- Use smaller batch size (edit `rl/ppo_agent.py` or `rl/grpo_agent.py`)

## ✅ Status

All import issues are resolved. The training script is ready to use!

