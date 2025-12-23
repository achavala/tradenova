# 🔍 Signal Monitoring Guide

## Real-Time Signal Tracking

### Quick Start

```bash
# Terminal 3 - Signal Monitor
./monitor_signals.sh
```

**Or manually**:
```bash
tail -f logs/tradenova_daily.log | grep -E "signal|confidence|agent|ensemble|block|filter"
```

---

## 📊 What the Logs Show

### Signal Generation (🤖)

**Agent signals**:
```
🤖 NVDA: TrendAgent generated LONG signal (confidence: 0.45, reasoning: ...)
```

**RL signals**:
```
🧠 AAPL: RL predictor generated LONG signal (confidence: 0.52, reason: ...)
```

### Signal Evaluation (📊)

**Signal selection**:
```
📊 TSLA: Best signal selected - TrendAgent (LONG, confidence: 0.48)
📊 Signal evaluation for TSLA: confidence=0.48, agent=TrendAgent, direction=LONG, allowed=True
```

### Why No Trade (⏳)

**Confidence too low**:
```
⏳ Signal confidence too low for NVDA: 0.42 < 0.50 (waiting for better setup)
```

**No signals**:
```
⏸️  AAPL: No signal from multi-agent system (waiting for better conditions)
```

### Filters Blocking (🛡️)

**News filter**:
```
🛡️ Trading blocked by news filter: FOMC meeting (protecting capital during high-risk events)
```

**Risk manager**:
```
🛡️ Trade blocked for TSLA: Max positions reached (confidence: 0.55)
```

### Trade Execution (✅)

**Trade executed**:
```
✅ EXECUTING TRADE: NVDA LONG (confidence: 0.52, agent: TrendAgent, reasoning: ...)
```

---

## 🎯 Understanding the Messages

### Early Morning (9:30-10:00 AM)

**Expected**:
- ⏸️ No signals (market stabilizing)
- ⏳ Low confidence signals (0.30-0.45)
- 🛡️ News filter may be active

**This is NORMAL.**

### Mid-Morning (10:00-11:00 AM)

**Expected**:
- 🤖 Agent signals start appearing
- 📊 Signal evaluation happening
- ⏳ Most still below 0.50 threshold

**System is evaluating - this is GOOD.**

### Afternoon (11:00 AM-2:00 PM)

**Expected**:
- ✅ First trades may execute
- 📊 Higher confidence signals (0.50+)
- 🤖 Multiple agents generating signals

**Best window for first trades.**

---

## 📈 Dashboard Monitoring

### Key Metrics

1. **System Validation Status**
   - Shows all component status
   - Watch for any red indicators

2. **RL Confidence Histogram**
   - Early: Low/neutral distribution
   - Later: More activity

3. **Ensemble Disagreement**
   - High = No trades (expected early)
   - Low = Potential trades

---

## ✅ Success Indicators

**System is working correctly if you see**:

✅ Logs showing signal generation  
✅ Dashboard showing confidence levels  
✅ System validation: All green  
✅ No errors  
✅ Stable confidence distributions  
✅ Agent activity in logs  

**Even if no trades execute, this confirms correct operation.**

---

## 🧘 Remember

**No trades in first hour = GOOD SIGN**

**System is protecting capital and waiting for quality setups.**

**This is professional behavior.**

---

*Signal Monitoring Guide - Track Why Trades Are/Are Not Executing*








