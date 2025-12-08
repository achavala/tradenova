# 🧪 TradeNova Validation Guide

## Professional Pre-Live Validation Protocol

This guide follows the same protocol used by hedge funds before deploying live capital.

---

## ✅ STEP 1: Dry-Run Mode (3 Days Minimum)

### Command
```bash
python run_daily.py --dry-run
```

### What to Validate

#### Signal Quality
- ✅ No excessive signal flipping (shouldn't change direction every cycle)
- ✅ Signals align with market conditions
- ✅ RL predictions are stable (not random noise)
- ✅ Ensemble agreement is reasonable (>50% on average)

#### Trading Behavior
- ✅ No excessive trades (shouldn't trade every cycle)
- ✅ Position sizing looks correct
- ✅ TP/SL levels are appropriate
- ✅ Risk manager triggers correctly

#### Logs & Warnings
- ✅ No errors in logs
- ✅ Warnings are minimal and expected
- ✅ Logs are readable and consistent
- ✅ No model degradation warnings

#### System Stability
- ✅ No crashes or hangs
- ✅ Memory usage is stable
- ✅ CPU usage is reasonable
- ✅ All components working together

### Success Criteria
- ✅ 3+ consecutive days without issues
- ✅ Signals look reasonable
- ✅ No unexpected behavior
- ✅ Logs are clean

---

## ✅ STEP 2: Paper Trading (2-3 Weeks Minimum)

### Command
```bash
python run_daily.py --paper
```

### What to Monitor

#### Execution Quality
- ✅ Fill rates (should be >90% for market orders)
- ✅ Slippage (should be minimal, <0.1% for liquid stocks)
- ✅ Execution timing (orders execute promptly)
- ✅ Order rejections (should be rare)

#### Position Management
- ✅ Position sizing is correct
- ✅ TP/SL orders execute properly
- ✅ Trailing stops work correctly
- ✅ Position exits are timely

#### Market Alignment
- ✅ GEX/IV regime alignment (trades match regime)
- ✅ Volatility regime matching
- ✅ News filter working (no trades during events)
- ✅ VIX filter working (blocks high VIX)

#### Performance Metrics
- ✅ Daily P&L is reasonable
- ✅ Win rate is acceptable (>50%)
- ✅ Sharpe ratio is positive
- ✅ Max drawdown is controlled

### Success Criteria
- ✅ 2-3 weeks of stable paper trading
- ✅ Fill rates >90%
- ✅ Slippage <0.1%
- ✅ Win rate >50%
- ✅ No major drawdowns

---

## ✅ STEP 3: Shadow Mode (Optional but Recommended)

### Command
```bash
python run_daily.py --shadow --save-signals ./logs/signals.json
```

### What This Does
- Captures all RL predictions
- Captures all multi-agent signals
- Captures ensemble decisions
- Saves to JSON and CSV for analysis

### Analysis
```python
import pandas as pd
import json

# Load signals
df = pd.read_csv('./logs/signals/signals_YYYYMMDD_HHMMSS.csv')

# Analyze RL confidence
print(df['rl_confidence'].describe())

# Analyze ensemble agreement
print(df['ensemble_agreement'].describe())

# Check signal consistency
print(df.groupby('symbol')['final_direction'].value_counts())
```

### Success Criteria
- ✅ Signals are captured correctly
- ✅ RL confidence is reasonable (not too low)
- ✅ Ensemble agreement is good (>60%)
- ✅ No obvious bugs in signal generation

---

## ✅ STEP 4: Small Capital Live (1-2 Weeks)

### Start With
- 1 contract per trade, OR
- 1-2% of normal position size

### Command
```bash
python run_daily.py
```

### What to Monitor

#### Daily Metrics
- ✅ Daily drawdown (should stay <5%)
- ✅ Daily P&L (should be reasonable)
- ✅ Trade count (not excessive)
- ✅ Risk triggers (shouldn't trigger often)

#### Model Performance
- ✅ RL confidence (should be >60% on average)
- ✅ Ensemble disagreements (should be <30%)
- ✅ Model degradation (shouldn't trigger)
- ✅ Prediction quality (signals make sense)

#### Risk Management
- ✅ Risk manager working correctly
- ✅ Daily loss limits respected
- ✅ Max drawdown limits respected
- ✅ Circuit breakers working

#### Dashboard
- ✅ Dashboard updates correctly
- ✅ Metrics look reasonable
- ✅ No anomalies in charts
- ✅ Equity curve is smooth

### Success Criteria
- ✅ 1-2 weeks of stable trading
- ✅ Daily drawdown <5%
- ✅ No risk limit breaches
- ✅ Model performance is stable
- ✅ Dashboard shows healthy metrics

### Scaling Plan
If all criteria met:
1. Week 3-4: Increase to 25% of normal size
2. Week 5-6: Increase to 50% of normal size
3. Week 7-8: Increase to 75% of normal size
4. Week 9+: Full size (if still stable)

---

## 📊 Validation Checklist

### Pre-Dry-Run
- [ ] All dependencies installed
- [ ] Config file configured
- [ ] Alpaca credentials set
- [ ] Logs directory exists
- [ ] Models directory exists

### After Dry-Run (3 days)
- [ ] No errors in logs
- [ ] Signals look reasonable
- [ ] No excessive trading
- [ ] System is stable
- [ ] Ready for paper trading

### After Paper Trading (2-3 weeks)
- [ ] Fill rates >90%
- [ ] Slippage <0.1%
- [ ] Win rate >50%
- [ ] No major issues
- [ ] Ready for small capital

### After Small Capital (1-2 weeks)
- [ ] Daily drawdown <5%
- [ ] No risk breaches
- [ ] Model is stable
- [ ] Performance is acceptable
- [ ] Ready to scale

---

## 🚨 Red Flags - Stop Trading If:

1. **Model Degradation**
   - RL accuracy drops below 40%
   - 5+ consecutive losses
   - Prediction entropy too high

2. **Risk Breaches**
   - Daily loss limit hit
   - Max drawdown exceeded
   - Circuit breaker triggered

3. **Execution Issues**
   - Fill rates <80%
   - Slippage >0.5%
   - Frequent order rejections

4. **System Issues**
   - Frequent crashes
   - Memory leaks
   - Unstable behavior

---

## 📈 Success Metrics

### Minimum Acceptable
- Win Rate: >50%
- Sharpe Ratio: >1.0
- Max Drawdown: <10%
- Daily Loss: <2%

### Good Performance
- Win Rate: >55%
- Sharpe Ratio: >1.5
- Max Drawdown: <7%
- Daily Loss: <1.5%

### Excellent Performance
- Win Rate: >60%
- Sharpe Ratio: >2.0
- Max Drawdown: <5%
- Daily Loss: <1%

---

## 🎯 Final Checklist Before Full Deployment

- [ ] Completed 3+ days dry-run
- [ ] Completed 2-3 weeks paper trading
- [ ] Completed 1-2 weeks small capital
- [ ] All metrics meet minimum criteria
- [ ] No red flags observed
- [ ] Dashboard shows healthy metrics
- [ ] Risk management working correctly
- [ ] Model performance is stable
- [ ] Execution quality is good
- [ ] Team is comfortable with system

---

**Status**: ✅ **Validation Protocol Ready**

**Next**: Follow steps 1-4 in order, only proceed to next step if current step passes all criteria.

